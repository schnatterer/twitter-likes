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
    tweets_by_id = {}
    # Initialize with some field so we can use the reference users_by_id and included_tweets_by_id
    includes_by_id = {'users': {}, 'tweets': {}}

    request_count = 0
    new_tweets_count = 0
    new_includes_count = {}
    pagination_token = None

    username = parsed_args.username
    bearer_token = os.environ.get('TWITTER_LIKES_BEARER_TOKEN')
    if not bearer_token:
        sys.stderr.write('Please set env var TWITTER_LIKES_BEARER_TOKEN')
        exit(1)

    json_file_name = 'likes.ndjson'
    json_from_file = load_json(json_file_name)
    if json_from_file:
        data = json_from_file['data']
        includes = json_from_file['includes']
        initialize_includes(includes, includes_by_id)
        initialize_tweets(data, tweets_by_id)
        print(f'Read {len(data)} tweets + includes: {countIncludes(includes)} from {json_file_name}')

    for response in get_liked_tweets(bearer_token, username, pagination_token):
        request_count += 1
        print(f'#\n# REQUEST #{request_count}. Next Page token: '
              f'{response.meta["next_token"] if "next_token" in response.meta else ""}\n#')

        # Start with includes, so includes_by_id is ready to be used in tweets-loop
        process_includes(response, includes, includes_by_id, new_includes_count)

        new_tweets_count += process_tweets(response, data, tweets_by_id, includes_by_id)

    write_json(json_file_name, data, includes)
    print(f'Done writing {len(data)} tweets ({new_tweets_count} new) + includes: {countIncludes(includes)}'
          f' (new {new_includes_count}) to {json_file_name}')


def process_tweets(response, data, tweets_by_id, includes_by_id):
    new_tweets_count = 0
    users_by_id = includes_by_id['users']
    included_tweets_by_id = includes_by_id['tweets']

    # response.data might be None on last page
    for tweet in response.data or []:
        # Avoid duplicate tweets, keep original
        if not str(tweet.id) in tweets_by_id:
            user = users_by_id[str(tweet['author_id'])]
            append_user_to_tweet_data(tweet.data, user)
            add_referenced_tweet_data_from_includes(tweet, included_tweets_by_id, users_by_id)

            tweets_by_id[tweet.id] = tweet.data
            data.append(tweet.data)
            tweet.data["saved_at"] = datetime.datetime.now()
            new_tweets_count += 1
            print(f'  Tweet added: {tweet.id}')
        else:
            # TODO update data but keep user?
            print(f'  Tweet already exists: {tweet.id}')

    return new_tweets_count


def process_includes(response, includes, includes_by_id, new_includes_count):

    # e.g. 'users' -> list of users
    for key, value in response.includes.items():
        if not (key in includes):
            includes[key] = []
        if not (key in includes_by_id):
            includes_by_id[key] = {}

        # e.g. individual user objects
        for include_object in value:
            # Update includes in order to avoid duplicate
            include_object_id = find_id(include_object.data)
            if include_object_id in includes_by_id[key]:
                print(f'  Included {key} updated: {include_object_id}')
                includes_by_id[key][include_object_id].update(include_object.data)
                includes[key][findIndexById(includes[key], include_object_id)] = include_object.data
            else:
                includes[key].append(include_object.data)
                includes_by_id[key][include_object_id] = include_object.data
                increment(new_includes_count, key)
                print(f'  Included {key} added: {include_object_id}')


def findIndexById(target_list, target_id):
    for index, element in enumerate(target_list):
        if 'id' in element:
            if element['id'] == target_id:
                return index
        elif 'media_key' in element:
            if element['media_key'] == target_id:
                return index
        else:
            print(f'Missing ID field in object: {element}')
            exit(2)
    return -1


def increment(new_includes, key):
    if key not in new_includes:
        new_includes[key] = 0
    new_includes[key] += 1


def countIncludes(includes):
    len_by_include = {}
    for key, value in includes.items():
        len_by_include[key] = len(value)
    return len_by_include


def initialize_includes(includes, includes_by_id):
    # e.g. 'users' -> list of users
    for key, value in includes.items():
        if not (key in includes_by_id):
            includes_by_id[key] = {}
        for include_object in value:
            include_object_id = find_id(include_object)
            includes_by_id[key][include_object_id] = include_object


def initialize_tweets(tweets, tweets_by_id):
    for tweet in tweets or []:
        tweets_by_id[tweet['id']] = tweet


def find_id(include):
    if 'id' in include:
        return include['id']
    elif 'media_key' in include:
        return include['media_key']
    else:
        print(f'Missing ID field in object: {include}')
        exit(2)


def add_referenced_tweet_data_from_includes(tweet, tweets_by_id, users_by_id):
    if 'referenced_tweets' in tweet:
        for ret_tweet in tweet['referenced_tweets']:
            if ret_tweet['id'] in tweets_by_id:
                actual_ref_tweet = tweets_by_id[ret_tweet['id']]
                ref_tweet_user = users_by_id[actual_ref_tweet['author_id']]

                append_user_to_tweet_data(actual_ref_tweet, ref_tweet_user)
            # else: # Tweet is likely deleted


def append_user_to_tweet_data(tweet, user):
    tweet["author"] = user
    tweet["author"]["saved_at"] = datetime.datetime.now()


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
