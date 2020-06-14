import os, string, random

# Games
class Game:
    # Constructor
    def __init__(self, room_name, password):
        self.room_name = room_name
        self.hashed_password = hash(password)
        self.room_id = self.generate_room_id()
        self.board = None
        self.player1 = None
        self.player2 = None
        self.target1 = ''
        self.target2 = ''

    # Creates a hash for the room
    def generate_room_id(self):
        string_length = 10
        character_set = string.ascii_lowercase + string.ascii_uppercase + string.digits
        return ''.join(random.choice(character_set) for _ in range(string_length))

    # Returns boolean of whether it's the correct password
    def check_password(self, password):
        return hash(password) == self.hashed_password

    # Adds a player to the room
    def add_player(self, nickname, session_id):
        if nickname is None:
            raise ValueError
            print("Cannot add player to room without a nickname")
        new_player = Player(nickname, session_id)
        if self.player1 is None:
            self.player1 = new_player
        elif self.player2 is None:
            self.player2 = new_player
        else:
            raise ValueError
            print("Cannot add player to an already full room")

    # Removes a player from the room
    def remove_player(self, session_id):
        which_player = self.which_player(session_id)
        if which_player == 1:
            self.player1 = None
        elif which_player == 2:
            self.player2 = None

    # Checks if the room has a player by session_id
    def has_player(self, session_id):
        return bool(self.which_player(session_id))

    # Checks if the session_id is for player 1, player 2, or neither
    def which_player(self, session_id):
        if self.player1 is not None and self.player1.session_id == session_id:
            return 1
        elif self.player2 is not None and self.player2.session_id == session_id:
            return 2
        else:
            return 0

    # Returns session_ids of players
    def player_ids(self):
        players = list(filter(lambda x:x is not None, [self.player1, self.player2]))
        return list(map(lambda x:x.session_id, players))

    # Checks if a room is full
    def is_full(self):
        return self.player1 is not None and self.player2 is not None

    # Player chooses a face for the opponent to guess
    def choose_target(self, session_id, row, col):
        which_player = self.which_player(session_id)
        if which_player == 1:
            self.target1 = self.board.grid1.cards[row][col]['face']
        elif which_player == 2:
            self.target2 = self.board.grid2.cards[row][col]['face']

    # Player flips one of their cards
    def flip_card(self, session_id, row, col):
        which_player = self.which_player(session_id)
        grid = self.board.grid1 if which_player == 1 else self.board.grid2
        grid.cards[row][col]['flipped'] = not grid.cards[row][col]['flipped']

    # Serializes the game state to json for a player
    def to_json(self, player):
        if self.board is None:
            return {}
        if player != 1 and player != 2:
            raise Exception("to_json takes arguments 1 or 2 only")
        other_player = player % 2 + 1
        myBoard = {
            'target': self.target1 if player == 1 else self.target2,
            'cards': self.board.to_json(player, True),
        }
        theirBoard = {
            'has_target': bool(self.target2 if player == 1 else self.target1),
            'cards': self.board.to_json(other_player, False)
        }
        return { 'myBoard': myBoard, 'theirBoard': theirBoard }

    # Setup the game board
    def set_up_game_board(self, facepack, num_rows, num_cols):
        self.board = Board(facepack, num_rows, num_cols)

    # Restar the game
    def restart_game(self):
        self.board = None
        self.target1 = None
        self.target2 = None

# Boards
class Board:
    # Constructor
    def __init__(self, facepack_name, num_rows, num_cols):
        # Load the Facepack
        all_faces = []
        try:
            all_faces = os.listdir('./static/facepacks/' + facepack_name)
            all_faces = list(filter(lambda x:not x.endswith('.DS_Store'), all_faces))
        except FileNotFoundError:
            raise Exception("Bad facepack name")
        except:
            raise Exception("Unable to open facepack")
        # Randomly choose the faces to play with
        total_faces = num_rows * num_cols
        if (len(all_faces) < total_faces):
            raise Exception("Not enough faces in facepack")
        print(all_faces)
        self.faces = random.sample(all_faces, total_faces)
        self.faces = list(map(lambda face:'/static/facepacks/' + facepack_name + '/' + face, self.faces))
        # Create boards for both players
        if num_rows <= 0 or num_cols <= 0:
            raise Exception("Number of rows and columns must be positive integers")
        self.grid1 = FaceGrid(self.faces, num_rows, num_cols)
        self.grid2 = FaceGrid(self.faces, num_rows, num_cols)

    # Serializes grid for the player or opponent
    def to_json(self, player, is_mine):
        if player == 1:
            return self.grid1.to_json(is_mine)
        else:
            return self.grid2.to_json(is_mine)

# FaceGrid
class FaceGrid:

    # Constructor
    def __init__(self, faces, num_rows, num_cols):
        # Create a grid of cards
        self.cards = [[{ 'flipped': False, 'face': None } for _ in range(num_cols)] for _ in range(num_rows)]
        self.fill_faces(faces)

    # Fill the grid with faces
    def fill_faces(self, faces):
        random.shuffle(faces)
        i = 0
        for row in range(len(self.cards)):
            for col in range(len(self.cards[0])):
                self.cards[row][col]['face'] = faces[i]
                i += 1

    # Flip down a face in the grid
    def flip(self, row, col):
        self.cards[row][col]['flipped'] = True

    # Output as json
    def to_json(self, is_mine):
        if is_mine:
            return self.cards
        else:
            anonymize = lambda cell: { 'flipped': cell['flipped'] }
            return list(map(lambda row:(list(map(anonymize, row))), self.cards))

# Player
class Player:
    def __init__(self, nickname, session_id):
        self.nickname = nickname
        self.session_id = session_id
