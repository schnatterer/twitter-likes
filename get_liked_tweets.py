import tweepy
import dbm
import json
import datetime
import argparse

import creds  # you must create creds.py


def main(parsed_args):
    download_media = parsed_args.m  # if True, download all media on each tweet_input

    tweets_by_id = {}
    liked_tweets = []
    users_by_id = {}
    count = 0
    # TODO implement parameter to start at token, in order not to have to start from the beginning each time
    # For testing REQUEST #95. Next Page token: 7140dibdnow9c7btw423hqze86jj21we7kmj6wuea7587
    pagination_token = None

    # https://developer.twitter.com/en/docs/twitter-api/tweets/likes/api-reference/get-users-id-liked_tweets
    with dbm.open('likes.db', 'c') as db, open('likes.ndjson', 'at', buffering=1) as jsonfile:
        for response in get_liked_tweets(creds.bearer_token, creds.username, pagination_token):

            count = count + 1
            print(f'#\n# REQUEST #{count}. Next Page token: '
                  f'{response.meta["next_token"] if "next_token" in response.meta else ""}\n#')

            # This returns a lot of "not authorized" errors regarding mentions, in_reply_to_user_id, deleted tweets
            # printErrors(response)

            add_included_users(response, users_by_id)

            add_included_tweets(response, tweets_by_id)

            # TODO if interested, add polls and media from includes similar to users and tweets

            for tweet in response.data or []:
                user = users_by_id[tweet.author_id]
                tweets_by_id[tweet.id] = tweet

                tweet_id = str(tweet.id)
                if tweet_id not in db:
                    # We're working on plain "data" field so we can export it to JSON later
                    append_user_to_tweet_data(tweet, user)

                    add_referenced_tweet_data_from_includes(tweet, tweets_by_id, users_by_id)

                    tweet_json = json.dumps(dict(sorted(tweet.data.items())), cls=DateTimeEncoder)
                    db[tweet_id] = tweet_json
                    jsonfile.write(tweet_json + "\n")

                    liked_tweets.append(tweet)
                    print(f'Tweet #{len(liked_tweets)}, {tweet.data["created_at"]}: '
                          f'{tweet.data["author"]["name"]} @{tweet.data["author"]["username"]}\n  '
                          f'{tweet.data["text"]}')
                else:
                    print(tweet_id + " exists in db")
                    # TODO exit when param set

    print('Done.')


def print_errors(response):
    if len(response.errors) > 0:
        print(f'WARNING: Request returned {len(response.errors)} errors.')
        print(response.errors)


def add_referenced_tweet_data_from_includes(tweet_input, tweets_by_id, users_by_id):
    if tweet_input.referenced_tweets:
        for (ref_tweet, ret_tweet_dat) in \
                zip(tweet_input.referenced_tweets, tweet_input.data["referenced_tweets"]):
            if ref_tweet.id in tweets_by_id:
                actual_ref_tweet = tweets_by_id[ref_tweet.id]
                ref_tweet_user = users_by_id[actual_ref_tweet.author_id]

                append_user_to_tweet_data(actual_ref_tweet, ref_tweet_user)
                # Add ref tweet data into original tweet
                ret_tweet_dat |= actual_ref_tweet.data
            # else: # Tweet is likely deleted


def add_included_tweets(response, tweets_by_id):
    if 'tweets' in response.includes:
        for includedTweet in response.includes['tweets'] or []:
            tweets_by_id[includedTweet.id] = includedTweet


def add_included_users(response, users_by_id):
    if 'users' in response.includes:
        for user in response.includes['users'] or []:
            users_by_id[user.id] = user


def get_liked_tweets(bearer_token, username, pagination_token):
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


def append_user_to_tweet_data(tweet_input, user):
    tweet_input.data["author"] = user.data


class DateTimeEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, datetime.datetime):
            return str(z)
        else:
            return super().default(z)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get favourites from Twitter')
    parser.add_argument('-m', action='store_true', help='download all media in each post (photos and video)')
    args = parser.parse_args()
    main(args)
