from flask import Flask, request
import requests

app = Flask(__name__)

brave_key = 'BSAnLBXo1M0ViAYxmnpWZwbUsLJ0hiR'
search_url = 'https://api.search.brave.com/res/v1/web/search'


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/search')
def search():
    query = request.args.get('q')
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': brave_key
    }
    response = requests.get(search_url, params={'q': query}, headers=headers)
    return response.json()


if __name__ == '__main__':
    app.run(debug=True)
