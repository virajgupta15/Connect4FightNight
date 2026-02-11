import math
import random
import copy
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows the frontend to communicate with this backend


# ---------------------------------------------------------
# 1. COMPATIBILITY LAYER
# ---------------------------------------------------------
# These classes allow your existing AI code to work with the
# simple 2D array sent by the website.

class Slot:
    """Mocks the object structure: board.checkSpace(r,c).value"""

    def __init__(self, value):
        self.value = value


class GameBoardWrapper:
    """
    Wraps the raw list-of-lists board from the frontend
    into the object structure your AI code expects.
    """

    def __init__(self, raw_board):
        # The frontend sends Row 0 = Top.
        # Your AI logic assumes Row 0 = Bottom.
        # We reverse the list so your logic works correctly.
        self.board = raw_board[::-1]
        self.numRows = len(self.board)
        self.numColumns = len(self.board[0])
        self.winNum = 4

        # Calculate colFills (next available row index for each column)
        self.colFills = []
        for c in range(self.numColumns):
            filled_height = 0
            # Scan from bottom (0) to top
            for r in range(self.numRows):
                if self.board[r][c] != ' ':
                    filled_height = r + 1
                else:
                    self.colFills.append(r)
                    break
            # If column is full, the next open slot is index numRows (out of bounds)
            if len(self.colFills) <= c:
                self.colFills.append(self.numRows)

    def checkSpace(self, r, c):
        # Bounds check
        if r < 0 or r >= self.numRows or c < 0 or c >= self.numColumns:
            return Slot("INVALID")
        return Slot(self.board[r][c])

    def addPiece(self, c, player_name):
        row = self.colFills[c]
        if row < self.numRows:
            self.board[row][c] = player_name
            self.colFills[c] += 1

    def removePiece(self, c):
        row = self.colFills[c] - 1
        if row >= 0:
            self.board[row][c] = ' '
            self.colFills[c] -= 1

    def checkFull(self):
        # If any column has space, board is not full
        for c in range(self.numColumns):
            if self.colFills[c] < self.numRows:
                return False
        return True

    def checkWin(self):
        # Standard Connect 4 Win Check
        # Horizontal
        for r in range(self.numRows):
            for c in range(self.numColumns - 3):
                p = self.board[r][c]
                if p != ' ' and p == self.board[r][c + 1] == self.board[r][c + 2] == self.board[r][c + 3]:
                    return True
        # Vertical
        for r in range(self.numRows - 3):
            for c in range(self.numColumns):
                p = self.board[r][c]
                if p != ' ' and p == self.board[r + 1][c] == self.board[r + 2][c] == self.board[r + 3][c]:
                    return True
        # Diagonal /
        for r in range(self.numRows - 3):
            for c in range(self.numColumns - 3):
                p = self.board[r][c]
                if p != ' ' and p == self.board[r + 1][c + 1] == self.board[r + 2][c + 2] == self.board[r + 3][c + 3]:
                    return True
        # Diagonal \
        for r in range(3, self.numRows):
            for c in range(self.numColumns - 3):
                p = self.board[r][c]
                if p != ' ' and p == self.board[r - 1][c + 1] == self.board[r - 2][c + 2] == self.board[r - 3][c + 3]:
                    return True
        return False


# ---------------------------------------------------------
# 2. YOUR AI PLAYER CLASS
# ---------------------------------------------------------

class Player:
    # strategy constants
    SCORE_WIN = 10000000
    SCORE_BLOCK_REQ = -999999
    WEIGHT_AI_THREAT = 500
    WEIGHT_OPP_THREAT = 1000
    WEIGHT_AI_SETUP = 30
    WEIGHT_AI_SETUP_WEAK = 15
    WEIGHT_OPP_SETUP = 8
    WEIGHT_ZUGZWANG = 100

    def __init__(self, name):
        self.name = name
        self.numExpanded = 0
        self.numPruned = 0
        self.moveTimes = []
        self.numNodesExpandedPerMove = []
        self.numPrunedPerMove = []

    def getMoveAlphaBeta(self, gameBoard):
        self.numPruned = 0
        self.numExpanded = 0

        start_expanded = self.numExpanded
        start_pruned = self.numPruned

        best_score = float("-inf")
        best_move = None
        search_depth = self.get_adaptive_depth(gameBoard, ab=True)
        alpha, beta = float("-inf"), float("inf")
        available = self.availableMoves(gameBoard)

        if not available: return 0
        best_move = available[0]

        for c in available:
            gameBoard.addPiece(c, self.name)
            score = self.minimaxAlphaBeta(search_depth, False, gameBoard, alpha, beta)
            gameBoard.removePiece(c)

            if score > best_score:
                best_score = score
                best_move = c

            alpha = max(alpha, score)

        self.numNodesExpandedPerMove.append(self.numExpanded - start_expanded)
        self.numPrunedPerMove.append(self.numPruned - start_pruned)
        return best_move

    def get_adaptive_depth(self, gameBoard, ab=False):
        return 7
        b = gameBoard.numColumns
        if ab:
            if b <= 6:
                return 7
            elif b == 7:
                return 5  # Reduced slightly for web performance
            elif b >= 8:
                return 4
        else:
            if 1 <= b <= 4:
                return 6
            elif b == 5:
                return 5
            elif b <= 7:
                return 4
            elif b >= 8:
                return 2
        return 4

    def availableMoves(self, gameBoard):
        top_row = gameBoard.numRows - 1
        availableCols = [c for c in range(gameBoard.numColumns)
                         if gameBoard.checkSpace(top_row, c).value == ' ']
        center_index = gameBoard.numColumns // 2
        availableCols.sort(key=lambda x: abs(x - center_index))
        return availableCols

    def minimaxAlphaBeta(self, depth, is_maximising, gameBoard, alpha, beta):
        self.numExpanded += 1

        if gameBoard.checkWin():
            return (self.SCORE_WIN + depth) if not is_maximising else -(self.SCORE_WIN + depth)

        if gameBoard.checkFull() or depth == 0:
            return 0 if gameBoard.checkFull() else self.evaluate_board(gameBoard)

        if is_maximising:
            score = float("-inf")
            for c in self.availableMoves(gameBoard=gameBoard):
                gameBoard.addPiece(c, self.name)
                score = max(score, self.minimaxAlphaBeta(depth - 1, False, gameBoard, alpha, beta))
                gameBoard.removePiece(c)
                alpha = max(alpha, score)
                if alpha >= beta:
                    self.numPruned += 1
                    break
            return score
        else:
            score = float("inf")
            opponent_name = 'O' if self.name == 'X' else 'X'
            for c in self.availableMoves(gameBoard=gameBoard):
                gameBoard.addPiece(c, opponent_name)
                score = min(score, self.minimaxAlphaBeta(depth - 1, True, gameBoard, alpha, beta))
                gameBoard.removePiece(c)
                beta = min(beta, score)
                if alpha >= beta:
                    self.numPruned += 1
                    break
            return score

    def evaluate_board(self, gameBoard):
        score = 0
        center_col_idx = gameBoard.numColumns // 2
        center_count = sum(
            1 for r in range(gameBoard.numRows) if gameBoard.checkSpace(r, center_col_idx).value == self.name)
        score += center_count * 10

        rows = gameBoard.numRows
        cols = gameBoard.numColumns
        heights = gameBoard.colFills
        win_num = gameBoard.winNum

        board_data = [[gameBoard.checkSpace(r, c).value for r in range(rows)] for c in range(cols)]
        ai_has_advantage = (rows * cols) % 2 != 0

        # UNDERCUTTING Logic
        lowest_threat_rows = [rows + 1] * cols
        for c in range(cols):
            for r in range(rows - win_num + 1):
                # Vertical Window: board_data[c][r : r+win_num]
                # Fix: board_data is [col][row]
                window = board_data[c][r: r + win_num]
                if window.count(' ') == 1:
                    if window.count('X') == win_num - 1 or window.count('O') == win_num - 1:
                        empty_offset = window.index(' ')
                        lowest_threat_rows[c] = r + empty_offset
                        break

                        # Scan Windows
        # Horizontal
        for r in range(rows):
            row_array = [board_data[c][r] for c in range(cols)]
            for c in range(cols - win_num + 1):
                window = row_array[c: c + win_num]
                score += self.evaluate_window(window, self.name, r, c, 0, 1, heights, ai_has_advantage,
                                              lowest_threat_rows)

        # Vertical
        for c in range(cols):
            col_array = board_data[c]
            for r in range(rows - win_num + 1):
                window = col_array[r: r + win_num]
                score += self.evaluate_window(window, self.name, r, c, 1, 0, heights, ai_has_advantage,
                                              lowest_threat_rows)

        # Diagonal /
        for r in range(rows - win_num + 1):
            for c in range(cols - win_num + 1):
                window = [gameBoard.checkSpace(r + i, c + i).value for i in range(win_num)]
                score += self.evaluate_window(window, self.name, r, c, 1, 1, heights, ai_has_advantage,
                                              lowest_threat_rows)

        # Diagonal \
        for r in range(win_num - 1, rows):
            for c in range(cols - win_num + 1):
                window = [gameBoard.checkSpace(r - i, c + i).value for i in range(win_num)]
                score += self.evaluate_window(window, self.name, r, c, -1, 1, heights, ai_has_advantage,
                                              lowest_threat_rows)

        return score

    def evaluate_window(self, window, piece, start_r, start_c, dr, dc, heights, ai_has_advantage, lowest_threat_rows):
        score = 0
        win_length = len(window)
        piece_count = window.count(piece)
        empty_count = window.count(' ')
        opponent_count = len(window) - piece_count - empty_count

        if opponent_count > 0 and piece_count > 0: return 0
        is_vertical = (dc == 0)

        if (piece_count == win_length - 1 or opponent_count == win_length - 1) and empty_count == 1:
            empty_idx = window.index(' ')
            empty_r = start_r + (empty_idx * dr)
            empty_c = start_c + (empty_idx * dc)

            if not is_vertical:
                if heights[empty_c] != empty_r:
                    if empty_r > lowest_threat_rows[empty_c]:
                        return 0

            weight = 0
            if heights[empty_c] == empty_r:
                if opponent_count == win_length - 1:
                    return self.SCORE_BLOCK_REQ
                weight = 1.0
            elif heights[empty_c] < empty_r:
                gap = empty_r - heights[empty_c]
                weight = 1 / (gap + 1)

            if piece_count == win_length - 1:
                score += (self.WEIGHT_AI_THREAT * weight)
            else:
                score -= (self.WEIGHT_OPP_THREAT * weight)

            is_odd_row = (empty_r % 2 == 0)
            threat_owner = self.name if (piece_count == win_length - 1) else ('O' if self.name == 'X' else 'X')

            is_good_for_X = False
            is_good_for_O = False

            if ai_has_advantage:
                if threat_owner == "O" and is_odd_row: is_good_for_O = True
                if threat_owner == "X" and not is_odd_row: is_good_for_X = True
            else:
                if threat_owner == "X" and is_odd_row: is_good_for_X = True
                if threat_owner == "O" and not is_odd_row: is_good_for_O = True

            zug_bonus = self.WEIGHT_ZUGZWANG * weight
            if is_good_for_X:
                score += zug_bonus if self.name == "X" else -zug_bonus
            if is_good_for_O:
                score += zug_bonus if self.name == "O" else -zug_bonus

        elif (piece_count == win_length - 2 or opponent_count == win_length - 2) and empty_count == 2:
            if piece_count == win_length - 2:
                str_window = "".join(window)
                connected_pattern = piece * (win_length - 2)
                is_connected = connected_pattern in str_window
                score += self.WEIGHT_AI_SETUP if is_connected else self.WEIGHT_AI_SETUP_WEAK
            else:
                score -= self.WEIGHT_OPP_SETUP

        return score


# ---------------------------------------------------------
# 3. FLASK ENDPOINT
# ---------------------------------------------------------

@app.route('/get-move', methods=['POST'])
def get_move():
    data = request.json
    raw_board = data.get('board')  # Safely get the board

    # --- SAFETY CHECK START ---
    # If the board is empty or missing, prevent the crash
    if not raw_board or len(raw_board) == 0:
        print("Wait! Received an empty board from the website. Defaulting to column 0.")
        return jsonify({'column': 0})
    # --- SAFETY CHECK END ---

    # Convert JS board (0/1/2) to char board (' '/'X'/'O')
    char_board = []
    for row in raw_board:
        new_row = []
        for cell in row:
            if cell == 1:
                new_row.append('X')
            elif cell == 2:
                new_row.append('O')
            else:
                new_row.append(' ')
        char_board.append(new_row)

    # Initialize Wrapper and Player
    game_board = GameBoardWrapper(char_board)
    ai_player = Player("X")

    # Calculate Best Move
    best_col = ai_player.getMoveAlphaBeta(game_board)

    # Fallback/Safety
    if best_col is None:
        best_col = 0

    return jsonify({'column': int(best_col)})


if __name__ == '__main__':
    app.run(debug=True)
