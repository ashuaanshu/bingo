import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import eventlet

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Game State
# Since we support "Two players max per room" efficiently, we can use a single dictionary
# to manage the state. For now, we'll support just one room 'lobby' for simplicity or
# dynamic rooms if needed.
# Given requirements: "Two players max per room", "Game starts automatically when both join".
# Let's assume a simplified matchmaking: Players join a specific room ID they agree on,
# or we just cycle them into the same 'default' room.
# To make it robust: Player enters name -> We put them in "room_1".
# State structure:
# games = {
#   'room_id': {
#       'players': {
#           'sid1': {'name': 'Alice', 'board': [...], 'lines': 0},
#           'sid2': {'name': 'Bob',   'board': [...], 'lines': 0}
#       },
#       'turn': 'sid1',
#       'status': 'waiting' | 'playing' | 'game_over',
#       'marked_numbers': set()
#   }
# }

games = {}
# Simple mapping from sid to room_id
player_rooms = {}

ROOM_ID = 'bingo_room'

def generate_board():
    """Generates a random 5x5 board with numbers 1-25."""
    numbers = list(range(1, 26))
    random.shuffle(numbers)
    # Return as 1D array for simplicity in indexing (0-24)
    return numbers

def check_win(board, marked_indices):
    """
    Checks if the board has 5 winning lines.
    board: list of 25 ints
    marked_indices: set of indices (0-24) that are cut
    Returns: count of completed lines
    """
    lines = 0
    # Rows
    for r in range(5):
        if all((r * 5 + c) in marked_indices for c in range(5)):
            lines += 1
    # Cols
    for c in range(5):
        if all((r * 5 + c) in marked_indices for r in range(5)):
            lines += 1
    # Diagonals
    if all((i * 6) in marked_indices for i in range(5)): # 0, 6, 12, 18, 24
        lines += 1
    if all((i * 4 + 4) in marked_indices for i in range(5)): # 4, 8, 12, 16, 20
        lines += 1

    return lines

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_game')
def on_join(data):
    name = data.get('name')
    sid = request.sid

    if ROOM_ID not in games:
        games[ROOM_ID] = {
            'players': {},
            'turn': None,
            'status': 'waiting',
            'marked_numbers': [] # List of actual numbers marked (1-25)
        }
    
    room = games[ROOM_ID]

    if len(room['players']) >= 2:
        emit('error_message', {'msg': 'Room is full. Wait for a slot.'})
        return

    # Add player
    join_room(ROOM_ID)
    player_rooms[sid] = ROOM_ID
    
    board = generate_board()
    room['players'][sid] = {
        'name': name,
        'board': board,
        'marked_indices': set(), # To track this player's specific board hits
        'lines': 0
    }

    # Notify everyone in room about update
    # We need to send specific data to each player (their own board)
    # But names can be broadcast.
    
    players_info = []
    for pid, pdata in room['players'].items():
        players_info.append({'name': pdata['name'], 'sid': pid})

    emit('player_joined', {'players': players_info}, room=ROOM_ID)

    # Check if game can start
    if len(room['players']) == 2:
        start_game(ROOM_ID)

def start_game(room_id):
    room = games[room_id]
    room['status'] = 'playing'
    player_sids = list(room['players'].keys())
    room['turn'] = player_sids[0] # Player 1 starts
    
    # Send start event to each player with their specific board
    for sid in player_sids:
        opponent_sid = player_sids[1] if sid == player_sids[0] else player_sids[0]
        opponent_name = room['players'][opponent_sid]['name']
        
        emit('game_start', {
            'board': room['players'][sid]['board'],
            'opponent': opponent_name,
            'turn': room['turn'], # sid of who's turn it is
            'your_sid': sid
        }, room=sid)

@socketio.on('make_move')
def on_move(data):
    sid = request.sid
    room_id = player_rooms.get(sid)
    number = data.get('number')
    
    if not room_id or room_id not in games:
        return

    room = games[room_id]
    
    if room['status'] != 'playing':
        return
    
    if room['turn'] != sid:
        emit('error_message', {'msg': "Not your turn!"})
        return

    if number in room['marked_numbers']:
        return # Already marked
        
    # Mark the number globally for the game
    room['marked_numbers'].append(number)
    
    # Update state for BOTH players
    game_over = False
    winner_name = None
    
    for pid, pdata in room['players'].items():
        # Find index of this number on player's board
        if number in pdata['board']:
            idx = pdata['board'].index(number)
            pdata['marked_indices'].add(idx)
            
            # Check lines
            lines_count = check_win(pdata['board'], pdata['marked_indices'])
            pdata['lines'] = lines_count
            
            if lines_count >= 5:
                game_over = True
                winner_name = pdata['name'] # First check wins. If both simultaneously? Logic implies Mover wins first usually, or handled.
                # Requirement: "First player to complete 5 lines wins"
                # If both complete on same turn? The current mover usually gets priority in turn-based, 
                # but if current move makes BOTH win, it's a draw? 
                # Let's say the person whose turn it was wins if they reach 5. 
    
    # Switch turn
    player_sids = list(room['players'].keys())
    next_turn = player_sids[1] if room['turn'] == player_sids[0] else player_sids[0]
    room['turn'] = next_turn
    
    # Broadcast move to both
    emit('number_marked', {
        'number': number,
        'turn': next_turn,
        'marked_numbers': room['marked_numbers'] # send all just in case
    }, room=room_id)
    
    # Send updated line counts / score
    for pid, pdata in room['players'].items():
        # Just send 'lines' to the player so they know their score
        # And maybe opponent score?
        opponent_sid = player_sids[1] if pid == player_sids[0] else player_sids[0]
        opp_lines = room['players'][opponent_sid]['lines']
        
        emit('score_update', {
            'your_lines': pdata['lines'],
            'opponent_lines': opp_lines
        }, room=pid)

    if game_over:
        room['status'] = 'game_over'
        emit('game_over', {'winner': winner_name}, room=room_id)

@socketio.on('reset_game')
def on_reset():
    sid = request.sid
    room_id = player_rooms.get(sid)
    if not room_id or room_id not in games:
        return
    
    room = games[room_id]
    # Only reset if game is over or requested? 
    # Let's simple reset: Clear state, regenerate boards, restart.
    
    room['status'] = 'waiting'
    room['marked_numbers'] = []
    
    # Keep players, just reset their boards/scores
    for pid in room['players']:
        room['players'][pid]['board'] = generate_board()
        room['players'][pid]['marked_indices'] = set()
        room['players'][pid]['lines'] = 0
        
    start_game(room_id)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    room_id = player_rooms.get(sid)
    
    if room_id in games:
        room = games[room_id]
        if sid in room['players']:
            name = room['players'][sid]['name']
            del room['players'][sid]
            # Notify opponent
            emit('player_left', {'name': name}, room=room_id)
            # Reset room
            games[room_id] = {
                'players': {}, # Clear all players? Or just waiting? 
                # Simplest: if one leaves, game kills. Remaining player must rejoin or wait.
                # Actually, usually keep remaining player.
                # Let's just reset the room completely for simplicity as requested 'Reset game for both players'
                 'turn': None,
                 'status': 'waiting',
                 'marked_numbers': []
            }
             # If a player remains, re-add them?
             # For simplicity, if one leaves, game over for other.
            
    if sid in player_rooms:
        del player_rooms[sid]

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
