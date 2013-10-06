from flask import Flask, send_from_directory
app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/compiled/<path:name>')
def compiled(name):
    if name.startswith('images/'):
        return send_from_directory('css', name)
    else:
        return send_from_directory('compiled', name)

@app.route('/images/<path:name>')
def images(name):
    return send_from_directory('images', name)


@app.route('/tileset/<path:name>')
def tileset(name):
    return send_from_directory('tileset', name)

if __name__ == '__main__':
    app.run(debug=1)
