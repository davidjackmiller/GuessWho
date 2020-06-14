#!/usr/bin/env python

from flask import Flask, render_template, request, url_for, redirect, session
from flask_socketio import SocketIO, emit, disconnect
from apscheduler.schedulers.background import BackgroundScheduler
import sys, os, time

from guesswho import Game, Board, FaceGrid, Player
    
# CREATE THE APPLICATION
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# WHILE I'M TOO LAZY TO MAKE A DATABASE
ACTIVE_CLIENTS = {};
GAMES = [];

""" ROUTING """

@app.route('/', methods=['GET', 'POST'])
def index(error = None):
    # Show an error if there is one
    if error is not None:
        return show_error(error)
    # If the user submitted the form to create/join a room
    if bool(request.form.to_dict()):
        # Parse the form
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        room = request.form.get('room')
        submit_action = request.form.get('submit')
        # Raise an error if any of the fields are empty
        error_fields = []
        if len(nickname) == 0:
            error_fields.append('nickname')
        if len(password) == 0:
            error_fields.append('password')
        if len(room) == 0:
            error_fields.append('room')
        if len(error_fields) > 0:
            return render_template('index.html', prefills=request.form, error_fields=error_fields)
        # Create a room
        if submit_action == 'Create Room':
            new_game = create_game(room, password)
            session['nickname'] = nickname
            return enter_room(new_game.room_id, nickname)
        # Join a room
        elif submit_action == 'Join Room':
            game = find_game(room)
            if game is None:
                return show_error('Room not found. Please check your room name and try again.')
            elif game.check_password(password):
                session['nickname'] = nickname
                return enter_room(game.room_id, nickname)
            else:
                return show_error('Incorrect password. Please try again.')
        # Throw error for invalid values of submit_action
        else:
            print('Invalid value for submit_action')
            return show_error('Something went wrong. Please try again.')
    # If the user is newly arriving at the site
    return render_template('index.html')

@app.route('/room/<room_id>', methods=['GET', 'POST'])
def room(room_id):
    game = find_game_by_id(room_id)
    # Add nickname to session if it exists
    form_nickname = request.form.get('nickname', '')
    if form_nickname:
        session['nickname'] = form_nickname
    # Error if the room ID is invalid
    if game is None:
        error = 'Room not found. Please check your room name and try again.'
        return redirect(url_for('index', error=error))
    # Error if the room is full
    elif game.is_full():
        error = 'Room is full. Please try again later or join a different room.'
        return redirect(url_for('index', error=error))
    # Show nickname form if the user has none
    elif 'nickname' not in session or not bool(session['nickname']):
        error_fields = [] if request.method == 'POST' else ['nickname']
        return render_template('nickname.html', error_fields=error_fields)
    # Show the game room
    else:
        facepacks = os.listdir('./static/facepacks')
        return render_template('game.html', room_id=room_id, facepacks=facepacks)

""" ROUTING UTILS """

def enter_room(room_id, nickname):
    session['nickname'] = nickname
    return redirect(url_for('room', room_id=room_id))

def show_error(error):
    return render_template('index.html', error=error)

""" GAME UTILS """

def create_game(room, password):
    new_game = Game(room, password)
    GAMES.append(new_game)
    return new_game

def find_room(room):
    for game in GAMES:
        if game.name == room:
            return game
    return None

def find_game_by_id(room_id):
    for game in GAMES:
        if game.room_id == room_id:
            return game 
    return None

""" MAIN """

if __name__ == '__main__':
    app.debug = True
    socketio.run(app, port=33507)

def emitGameUpdate(game):
    if game.player1 is not None:
        emit('game update', game.to_json(1), room=game.player1.session_id)
    if game.player2 is not None:
        emit('game update', game.to_json(2), room=game.player2.session_id)

def emitFullGameError(session_id):
    data = { 'destination_url': url_for('index') }
    emit('full game error', data, room=session_id)

""" SOCKETIO EVENTS """

# When a client connects
@socketio.on('connect')
def on_connect():
    global ACTIVE_CLIENTS
    ACTIVE_CLIENTS[request.sid] = time.time()

# # When a client disconnects
# @socketio.on('disconnect')
# def on_disconnect():
#     # Note the client doesn't really have a disconnect 
#     print('Client disconnected: ' + request.sid)
#     global ACTIVE_CLIENTS
#     ACTIVE_CLIENTS -= 1
#     print('Total Active Clients: ' + str(ACTIVE_CLIENTS))
#     print('Total Active Games: ' + str(len(GAMES)))

# When a client joins a room
@socketio.on('join')
def on_join(data):
    game_id = data['game_id']
    nickname = session['nickname']
    game = find_game_by_id(game_id)
    if game is not None:
        if game.is_full():
            emitFullGameError(request.sid)
        else:
            game.add_player(nickname, request.sid)
            emitGameUpdate(game)

""" INACTIVE USER MANAGEMENT """

# Hearbeat to detect clients who left
@socketio.on('heartbeat')
def on_heartbeat():
    global ACTIVE_CLIENTS
    new_timestamp = time.time()
    ACTIVE_CLIENTS[request.sid] = new_timestamp

# Kick inactive users based on last heartbeat
def kick_inactive_users():
    global ACTIVE_CLIENTS
    cutoff = time.time() - 10 # 10 seconds ago
    for game in GAMES:
        for session_id in game.player_ids():
            if ACTIVE_CLIENTS[session_id] < cutoff:
                ACTIVE_CLIENTS.pop(session_id, None)
                game.remove_player(session_id)

# Start a scheduler to check inactive users
scheduler = BackgroundScheduler()
job = scheduler.add_job(kick_inactive_users, 'interval', seconds=3)
scheduler.start()

# When a client leaves a room
# @socketio.on('leave')
# def on_leave(data):
#     room = data['room']
#     game = find_game(room)
#     if game is not None:
#         game.remove_player(request.sid)
#         emitGameUpdate(game)

""" GAME SETUP EVENTS """

# When a user sets the game settings
@socketio.on('game settings')
def on_game_settings(data):
    room_id = data['room_id']
    facepack = data['facepack']
    rows, cols = int(data['rows']), int(data['cols'])
    game = find_game_by_id(room_id)
    if game is not None:
        game.set_up_game_board(facepack, rows, cols)
        emitGameUpdate(game)

# When a user chooses a target
@socketio.on('choose target')
def on_choose_target(data):
    room_id = data['room_id']
    row, col = data['row'], data['col']
    game = find_game_by_id(room_id)
    if game is not None:
        game.choose_target(request.sid, row, col)
        emitGameUpdate(game)

""" GAMEPLAY EVENTS """

# When a user flips a face on their board
@socketio.on('flip card')
def on_flip_card(data):
    room_id = data['room_id']
    row, col = data['row'], data['col']
    game = find_game_by_id(room_id)
    if game is not None:
        game.flip_card(request.sid, row, col)
        emitGameUpdate(game)

@socketio.on('guess')
def on_guess(data):
    room_id = data['room_id']
    row, col = data['row'], data['col']
    game = find_game_by_id(room_id)
    if game is not None:
        #game.flip_card(request.sid, row, col)
        emitGameUpdate(game)

@socketio.on('restart game')
def on_guess(data):
    room_id = data['room_id']
    game = find_game_by_id(room_id)
    if game is not None:
        game.restart_game()
        emitGameUpdate(game)




