from __future__ import print_function
from __future__ import nested_scopes

import datetime
import argparse
import requests
import json
import webbrowser

import os
import os.path

class PocketAPI(object):
    """Basic orchestration of the Pocket API
    """

    def __init__(self, consumer_key, redirect_uri):
        self.consumer_key = consumer_key
        self.redirect_uri = redirect_uri

        self.request_token = None
        self.access_token = None

    def authenticate_interactively(self):

        print("Getting request token for app")
        self.get_request_key()

        print("Attempting to authorize")
        self.authorize()

        while self.access_token is None:
            print("Not yet authorized. Opening web browser")
            self.load_web_browser()
            raw_input("Press enter when you have completed the authorization, or Ctrl+C to give up.")
            self.authorize()

    def search(self, **kwargs):
        kwargs.update({'consumer_key': self.consumer_key, 'access_token': self.access_token})

        r = requests.post(
            'https://getpocket.com/v3/get',
            data=kwargs,
            headers={'x-accept': 'application/json'}
        )

        return json.loads(r.text)

    # Helpers

    def get_request_key(self):
        r = requests.post(
            'https://getpocket.com/v3/oauth/request',
            data={'consumer_key': self.consumer_key, 'redirect_uri': self.redirect_uri},
            headers={'x-accept': 'application/json'}
        )

        self.request_token = json.loads(r.text)['code']

    def load_web_browser(self):
        webbrowser.open('https://getpocket.com/auth/authorize?request_token=' + self.request_token + '&redirect_uri=' + self.redirect_uri)

    def authorize(self):
        r = requests.post(
            'https://getpocket.com/v3/oauth/authorize',
            data={'consumer_key': self.consumer_key, 'code': self.request_token},
            headers={'x-accept': 'application/json'}
        )

        if r.status_code != 200:
            self.access_token = None
        else:
            self.access_token = json.loads(r.text)['access_token']



#
# Run export
#

def main():
    parser = argparse.ArgumentParser(description='Export Pocket posts to blot.im files')
    parser.add_argument('directory', metavar='directory', help='Directory where files will be stored')
    parser.add_argument('--consumer-key', dest='consumer_key', required=True, help='Pocket app consumer key')
    parser.add_argument('--redirect-uri', dest='redirect_uri', default='https://http.cat/200', help='URI to redirect to after authentication, not terribly important.')
    parser.add_argument('--tag', dest='tag', help="Tag to filter by")
    parser.add_argument('--favorites', dest='favorites', action='store_true', help="Only export favorites")
    parser.add_argument('--state', dest='state', metavar='unread|archive|all', help="Only return items in the given state")
    parser.add_argument('--content_type', dest='content_type', metavar='article|video|image', help="Only return items of the given type")
    parser.add_argument('--search', dest='search', metavar='"search text"', help="Free text search")

    args = parser.parse_args()

    print("Authenticating with Pocket")
    pocket = PocketAPI(args.consumer_key, args.redirect_uri)
    pocket.authenticate_interactively()

    query = {}
    if args.tag:
        query['tag'] = args.tag
    if args.favorites:
        query['favorite'] = '1'
    if args.state:
        query['state'] = args.state
    if args.content_type:
        query['contentType'] = args.content_type

    print("Running query")
    results = pocket.search(sort='newest', detailType='complete', **query)

    if not os.path.exists(args.directory):
        os.mkdir(args.directory)

    for id, item in results['list'].items():
        title = item['resolved_title'].encode('utf-8')
        url = item['resolved_url'].encode('utf-8')
        tags = [t.encode('utf-8') for t in item['tags'].keys()] if 'tags' in item else []
        excerpt = item['excerpt'].encode('utf-8')
        authors = [a['name'].encode('utf-8') for a in item['authors'].values()] if 'authors' in item else []
        timestamp = datetime.date.fromtimestamp(int(item['time_updated']))

        filename = os.path.join(args.directory, "".join(x for x in title if x not in "\/:*?<>|") + '.md')

        with open(filename, 'w') as file:
            print("#", title, file=file)
            if len(authors) > 0:
                print("By", ", ".join(authors), file=file)
            print("", file=file)

            print("Date:", timestamp.isoformat(), file=file)
            print("Tags:", ", ".join(tags), file=file)
            print("", file=file)
            print(excerpt, file=file)
            print("[Read more...](%s)" % url, file=file)

if __name__ == '__main__':
    main()
