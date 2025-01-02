# twitter-likes

Download your twitter likes using an enhanced version of https://gist.github.com/datagrok/74a71f572493e603919e

## Run inside container

```shell
  TOKEN='A...' # The two spaces avoid storing the secret in shell history
docker run --rm --pull=always -u=$(id -u) \
  -v $(pwd):/cwd -e TWITTER_LIKES_BEARER_TOKEN=$TOKEN \
  ghcr.io/schnatterer/twitter-likes \
  /scripts/get_liked_tweets.py <username>
```

TODO template

## Run locally
### prereqs

- Install python 3
- Install gdbm: `brew install gdbm`
- Create an application at [developer.twitter.com/en/apps](https://developer.twitter.com/en/apps)
- Create `creds.py` with the following from your application

```
username = "datagrok"
consumer_key = "..."
consumer_secret = "..."
access_token = "..."
access_token_secret = "..."
```

- `make venv` to create the virtual env

### commands

* `make fetch` downloads favs to favs.db and favs.ndjson  
* `TWITTER_LIKES_BEARER_TOKEN='A...' make fetchv2 <username>` downloads likes to `favs.ndjson`  
  * Downloads in [Twitter v2 API](https://developer.twitter.com/en/docs/twitter-api/tweets/likes/api-reference/get-users-id-liked_tweets) format.
  * In addition, for easier processing, embeds 
    * full tweet in `referenced_tweets` and
    * full `author` object in all tweets and `referenced_tweets` in `data` (not `includes`)
  * Can be run incrementally. Keeps authors in `data` only updates other data, and `includes`
* `make dump` extract favs from favs.db to stdout  
* `make` to show all options

## alternatives

[IFTTT](https://ifttt.com/applets/113241p-save-the-tweets-you-like-on-twitter-to-a-google-spreadsheet) - however it won't log tweets older than the previous liked tweet (eg: a tweet from 2018 if the last liked tweet was in 2019). I'm assuming it's using the `since_id` filter of the last recorded tweet when calling the [favourites api](https://developer.twitter.com/en/docs/tweets/post-and-engage/api-reference/get-favorites-list).

[dogsheep/twitter-to-sqlite](https://github.com/dogsheep/twitter-to-sqlite) - save favourites (and other things) to sqllite. Has the same API limits of max 3170 tweets at a time.
