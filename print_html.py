import json
import jinja2


def main():
    title = 'My twitter likes'
    output_file = 'my-likes.html'
    tweets_by_id = {}
    users_by_id = {}

    f = open('likes.ndjson', "r")
    json_data = json.loads(f.read())
    f.close()

    tweets = json_data['data']
    add_included_users(json_data, users_by_id)
    add_included_tweets(json_data, tweets_by_id)

    for tweet in tweets or []:
        user = users_by_id[tweet['author_id']]
        append_user_to_tweet_data(tweet, user)
        add_referenced_tweet_data_from_includes(tweet, tweets_by_id, users_by_id)

    subs = jinja2.Environment(
        loader=jinja2.FileSystemLoader('./')
    ).get_template('template.html').render(title=title, tweets=tweets)

    with open(output_file, 'w') as f:
        f.write(subs)


def add_included_users(response, users_by_id):
    if 'users' in response['includes']:
        for user in response['includes']['users'] or []:
            users_by_id[user['id']] = user


def add_included_tweets(response, tweets_by_id):
    if 'tweets' in response['includes']:
        for includedTweet in response['includes']['tweets'] or []:
            tweets_by_id[includedTweet['id']] = includedTweet


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


if __name__ == '__main__':
    main()
