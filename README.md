# My-Taste
Get your movie ratings from Tast.io

## Dependencies
- **Brotli**: `pip install brotli` - this is used to decompress the JSON result from taste.
- **Requests**: `pip install requests` - this handles network requests
- **JSONSchema**: `pip install jsonschema` - validates configuration

## Usage examples
- `my-taste.py -e your@email.com -p y0urP4$$w0rd -j -c` export your rating list as a JSON (`-j`) and as a CSV(`-c`).
- `my-taste.py -C my_taste_conf.json` use configuration file as input.

## Configuration example
`{"email": "your@email.com",
  "password": "y0urP4$$w0rd",
  "json": true,
  "csv": false}`
"json", and "csv" fields are not required, if no option is provided, json result will be created.
