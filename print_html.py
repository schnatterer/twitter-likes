import json
import jinja2


def main():
    # TODO re-use this template?
    # https://github.com/kensanata/mastodon-backup
    title = 'My twitter likes'
    output_file = 'my-likes.html'

    f = open('likes.ndjson', "r")
    json_data = json.loads(f.read())
    f.close()

    tweets = json_data['data']

    subs = jinja2.Environment(
        loader=jinja2.FileSystemLoader('./')
        # TODO keep '\n' in value text
        # TODO replace t.co with real URL
    ).get_template('template.html').render(title=title, tweets=tweets)

    with open(output_file, 'w') as f:
        f.write(subs)


def recursive_iter(obj):
    if isinstance(obj, dict):
        for item in obj.values():
            yield from recursive_iter(item)
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for item in obj:
            yield from recursive_iter(item)
    else:
        yield obj


if __name__ == '__main__':
    main()
