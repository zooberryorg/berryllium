# Berryllium

Berryllium is the software behind the mod-hosting website [ZooBerry](https://www.zooberry.org/). It is a Django app!

(Still in development and not yet live)

## Setup

1. Clone the repository

```bash
git clone git@github.com:zooberryorg/berryllium.git
```

2. Create a Python virtual environment and activate it

3. Install the dependencies

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root of the project and add the following environment variables (no variables yet)

5. Build containers

```bash
docker-compose build
```

Local server instance will be accessible at `http://localhost:8001`

6. Run the containers

```bash
docker-compose up
```

## Development

### UX/UI

To setup UX/UI development, make sure you have Node.js and npm installed. In a separate terminal, run Tailwind CLI to watch for changes in the templates and update the project's CSS file:

```bash
npx @tailwindcss/cli -i ./.tw/input.css -o ./berryllium/shared/static/shared/css/be.css --watch
```

For more information, see the [Tailwind CLI documentation](https://tailwindcss.com/docs/installation/tailwind-cli).

### Linters and Formatters

For Django templates, we use [djlint](https://djlint.com/). It can be used as both a linter and a formatter.

To lint: 

```bash
djlint .
```

To format:

```bash
djlint . --reformat
```

For Python code linting and formatting, we use [Ruff](https://docs.astral.sh/ruff/).

To lint:

```bash
ruff check
```

To format:

```bash
ruff format
```
