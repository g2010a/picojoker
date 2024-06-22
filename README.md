Joke sources:
- https://github.com/Sv443-Network/JokeAPI/
- https://github.com/15Dkatz/official_joke_api/
- And many, many pages for the jokes in Spanish

Processing:
```bash
# Get one set of English jokes
curl https://raw.githubusercontent.com/15Dkatz/official_joke_api/master/jokes/index.json -o jokes-official.private.json
cat jokes-official.private.json \
| jq 'map(select(.type != "programming"))' \
| jq -c '.[] | [.setup, .punchline]' \
> jokes-en.min.json

# Get another set of English jokes
curl https://raw.githubusercontent.com/Sv443-Network/JokeAPI/main/data/jokes/regular/jokes-en.json -o jokes-en.private.json
cat jokes-en.private.json \
| jq -c -r '.jokes[] 
| select(
        .flags.nsfw == false
    and .flags.racist == false
    and .flags.sexist == false
    and .flags.explicit == false
    and .setup != null
    and .delivery != null
    and .category != "Programming")
| [.setup, .delivery]' \
>> jokes-en.min.json

# Remove duplicates
awk '!seen[$0]++' jokes-en.min.json > temp.json && mv temp.json jokes-en.min.json

# Get German jokes
curl https://raw.githubusercontent.com/Sv443-Network/JokeAPI/main/data/jokes/regular/jokes-de.json -o jokes-de.private.json
cat jokes-de.private.json \
| jq -c -r '.jokes[] 
| select(
        .flags.nsfw == false
    and .flags.racist == false
    and .flags.sexist == false
    and .flags.explicit == false
    and .setup != null
    and .delivery != null
    and .category != "Programming")
| [.setup, .delivery]' \
> jokes-de.min.json

# TODO: enrich them with https://witzapi.de/api-docs/#/joke/get_api_joke_
```