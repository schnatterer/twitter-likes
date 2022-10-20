import os
import sys
from os.path import exists
import tweepy
import json
import datetime
import argparse


def main(parsed_args):

    data = []
    includes = {}
    count = 0
    pagination_token = None

    username = args.username
    bearer_token = os.environ.get('TWITTER_LIKES_BEARER_TOKEN')
    if not bearer_token:
        sys.stderr.write('Please set env var TWITTER_LIKES_BEARER_TOKEN')
        exit(1)

    json_file_name = 'likes.ndjson'
    json_from_file = load_json(json_file_name)
    if json_from_file:
        data = json_from_file['data']
        includes = json_from_file['includes']
        print(f'Read {len(data)} tweets from {json_file_name}')

    for response in get_liked_tweets(bearer_token, username, pagination_token):
        count = count + 1
        print(f'#\n# REQUEST #{count}. Next Page token: '
              f'{response.meta["next_token"] if "next_token" in response.meta else ""}\n#')

        # response.data might be None on last page
        for tweet in response.data or []:
            data.append(tweet.data)

        for key, value in response.includes.items():
            # e.g. 'users' -> list of users
            if not (key in includes):
                includes[key] = []
            for includeObject in value:
                includes[key].append(includeObject.data)

    write_json(json_file_name, data, includes)
    print(f'Done writing {len(data)} tweets')


def write_json(json_file_name, data, includes):
    # Write whole file, don't append
    f = open(json_file_name, "w")
    f.write(json.dumps({"data": data, "includes": includes}, cls=DateTimeEncoder) + "\n")
    f.close()


def load_json(json_file_name):
    if exists(json_file_name):
        f = open(json_file_name, "r")
        json_data = json.loads(f.read())
        f.close()
        return json_data
    return None


def get_liked_tweets(bearer_token, username, pagination_token):
    # https://developer.twitter.com/en/docs/twitter-api/tweets/likes/api-reference/get-users-id-liked_tweets

    client = tweepy.Client(bearer_token, wait_on_rate_limit=True)

    response = client.get_user(username=username)
    user_id = response.data.id

    return tweepy.Paginator(client.get_liked_tweets, user_id,
                            # author_id needed to enable user_fields
                            expansions=["attachments.poll_ids", "attachments.media_keys", "author_id",
                                        "entities.mentions.username", "geo.place_id",
                                        "in_reply_to_user_id", "referenced_tweets.id",
                                        "referenced_tweets.id.author_id"],
                            user_fields=["created_at", "description", "entities", "id", "location", "name",
                                         "pinned_tweet_id", "profile_image_url", "protected",
                                         "public_metrics", "url", "username", "verified", "withheld"],
                            tweet_fields=["attachments", "author_id", "context_annotations",
                                          "conversation_id", "created_at", "entities", "geo", "id",
                                          "in_reply_to_user_id", "lang", "public_metrics",
                                          "possibly_sensitive", "referenced_tweets", "reply_settings",
                                          "source", "text", "withheld"],
                            media_fields=["duration_ms", "height", "media_key", "preview_image_url",
                                          "type", "url", "width", "public_metrics", "alt_text",
                                          "variants"],
                            place_fields=["contained_within", "country", "country_code", "full_name",
                                          "geo", "id", "name", "place_type"],
                            poll_fields=["duration_minutes", "end_datetime", "id", "options",
                                         "voting_status"],
                            pagination_token=pagination_token)
    # fields leading to "not authorized": "non_public_metrics", "organic_metrics", "promoted_metrics"


class DateTimeEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, datetime.datetime):
            return str(z)
        else:
            return super().default(z)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get favourites from Twitter')
    parser.add_argument('username', metavar='username', type=str, help='twitter username to get likes for')
    args = parser.parse_args()
    main(args)
