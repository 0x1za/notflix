import os
import json
import click
import requests
import inquirer

from absl import logging
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

# Code of your application, which uses environment variables (e.g. from `os.environ` or
# `os.getenv`) as if they came from the actual environment.


@click.command()
@click.option("--title",
              prompt="Movie title",
              help="Movie title to search for.")
def app(title):
    """Simple program that populates your Notion movie database for you and
    your significant other.
    """
    results = omdb_get_movie(title)
    imdb_ids = json_extract(results, "imdbID")

    titles = merge_titles(
        json_extract(results, "Title"),
        json_extract(results, "Year"),
        json_extract(results, "Type"),
    )

    questions = [
        inquirer.List(
            "movie",
            message="Select movie from search results...",
            choices=results_tuple(titles, imdb_ids),
        ),
    ]
    answers = inquirer.prompt(questions)
    movie = omdb_get_movie(answers["movie"], by_id=True)

    # Check if movie is already in Notion database table.
    exists = search_database(movie["imdbID"], "IMDb ID")["results"]

    if len(exists) == 0:
        logging.info('Adding movie ' + movie['Title'] + ' to Notion...')
        create_notion_entry(movie)
        logging.info("Done...")
    elif len(exists) == 1:
        logging.warning('Skipping, entry already exists in database.')
    else:
        logging.fatal(
            "Something went wrong... extry might already exist in database")


def search_database(query, key):
    url = "https://api.notion.com/v1/databases/" + str(
        os.getenv("NOTION_DATABASE_ID")) + "/query"

    payload = json.dumps(
        {"filter": {
            "property": str(key),
            "text": {
                "equals": str(query)
            }
        }})

    headers = {
        'Notion-Version': '2021-08-16',
        'Authorization': os.getenv("NOTION_INTEGRATION_SECRET_KEY"),
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()


def create_notion_entry(data):
    url = "https://api.notion.com/v1/pages"

    payload = json.dumps({
        "parent": {
            "database_id": os.getenv("NOTION_DATABASE_ID")
        },
        "properties": {
            "title": {
                "title": [{
                    "text": {
                        "content": "" + str(data["Title"]) + ""
                    }
                }]
            },
            "IMDb ID": {
                "rich_text": [{
                    "text": {
                        "content": "" + str(data["imdbID"]) + ""
                    }
                }]
            },
            "Plot": {
                "rich_text": [{
                    "text": {
                        "content": "" + str(data["Plot"]) + ""
                    }
                }]
            },
            "Year": {
                "rich_text": [{
                    "text": {
                        "content": "" + str(data["Year"]) + ""
                    }
                }]
            },
            "Run Time": {
                "rich_text": [{
                    "text": {
                        "content": "" + str(data["Runtime"]) + ""
                    }
                }]
            },
            "Genre": {
                "multi_select":
                generate_multi_select(data["Genre"].split(", "))
            },
            "Cast": {
                "multi_select":
                generate_multi_select(data["Actors"].split(", "))
            },
            "Star Rating": {
                "select": {
                    "name": metascore_to_stars(int(data["Metascore"]))
                }
            }
        }
    })
    headers = {
        'Notion-Version': '2021-08-16',
        'Authorization': os.getenv("NOTION_INTEGRATION_SECRET_KEY"),
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.status_code)
    return response.status_code


def metascore_to_stars(score):
    stars = None
    if score in range(0, 20):
        stars = "⭐"
    elif score in range(20, 40):
        stars = "⭐⭐"
    elif score in range(40, 61):
        stars = "⭐⭐⭐"
    elif score in range(61, 81):
        stars = "⭐⭐⭐⭐"
    elif score in range(81, 101):
        stars = "⭐⭐⭐⭐⭐"

    return stars


def results_tuple(titles, ids):
    results = []
    for idx, item in enumerate(titles):
        results.append((item, ids[idx]))
    return results


def merge_titles(titles, years, types):
    results = []
    for idx, item in enumerate(titles):
        results.append(item + " (" + str(years[idx]) + ") - " +
                       str(types[idx]))
    return results


def generate_multi_select(array):
    result = []
    for item in array:
        result.append({"name": str(item)})
    return result


def json_extract(obj, key):
    """Recursively fetch values from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values


def omdb_get_movie(query, by_id=False):
    if by_id is False:
        param = "s"
    else:
        param = "i"

    url = ("https://www.omdbapi.com/?apikey=" + str(os.getenv("OMDB_KEY")) +
           "&" + str(param) + "=" + str(query))
    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    return response.json()


if __name__ == "__main__":
    app()
