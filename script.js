const ROWS = 6;
const COLS = 7;
const PLAYER_AI = 1; // 'X' (Red)
const PLAYER_HUMAN = 2; // 'O' (Gold/Team Sam)

// PASTE YOUR RENDER URL HERE
const API_URL = "http://127.0.0.1:5000";

let board = [];
let currColumns = [];
let gameOver = false;
let currentPlayer = PLAYER_AI;

function startGame() {
    document.getElementById("landing-page").classList.remove("active");
    document.getElementById("landing-page").classList.add("hidden");
    document.getElementById("game-ui").classList.remove("hidden");
    document.getElementById("game-ui").classList.add("active");
    resetGame();
}
// ... Variables and Imports ...

function resetGame() {
    board = [];
    currColumns = [5, 5, 5, 5, 5, 5, 5];
    gameOver = false;
    currentPlayer = PLAYER_AI;
    document.getElementById("message-modal").classList.add("hidden");

    // Updated Text
    document.getElementById("turn-indicator").innerText = "SAM IS THINKING...";
    document.getElementById("turn-indicator").style.color = "#e74c3c"; // Red for Sam

    // IMPORTANT: Create the logic board
    for (let r = 0; r < ROWS; r++) {
        let row = [];
        for (let c = 0; c < COLS; c++) row.push(0);
        board.push(row);
    }

    // Render Board
    const boardElement = document.getElementById("board");
    boardElement.innerHTML = "";
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            let tile = document.createElement("div");
            tile.id = r.toString() + "-" + c.toString();
            tile.classList.add("cell");
            tile.addEventListener("click", () => setPiece(c));
            boardElement.appendChild(tile);
        }
    }

    aiMove();
}

function setPiece(c) {
    if (gameOver || currentPlayer !== PLAYER_HUMAN) return;

    let r = currColumns[c];
    if (r < 0) return;

    board[r][c] = PLAYER_HUMAN;
    let tile = document.getElementById(r.toString() + "-" + c.toString());
    tile.classList.add("player2", "falling");
    currColumns[c]--;

    if (checkWinner(PLAYER_HUMAN)) {
        endGame("YOU KNOCKED OUT SAM!", "GOLD");
        return;
    }
    if (currColumns.every(val => val < 0)) {
        endGame("DRAW! GO TO JUDGES.", "WHITE");
        return;
    }

    currentPlayer = PLAYER_AI;
    // Updated Text
    document.getElementById("turn-indicator").innerText = "SAM IS THINKING...";
    document.getElementById("turn-indicator").style.color = "#e74c3c";
    aiMove();
}

async function aiMove() {
    if (gameOver) return;

    const payload = { board: board };

    try {
        const response = await fetch(`${API_URL}/get-move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        let col = data.column;

        if (col !== null && currColumns[col] >= 0) {
            let r = currColumns[col];
            board[r][col] = PLAYER_AI;
            let tile = document.getElementById(r.toString() + "-" + col.toString());
            tile.classList.add("player1", "falling");
            currColumns[col]--;

            if (checkWinner(PLAYER_AI)) {
                endGame("SAM WINS BY KO", "RED");
                return;
            }
            if (currColumns.every(val => val < 0)) {
                endGame("DRAW! GO TO JUDGES.", "WHITE");
                return;
            }

            currentPlayer = PLAYER_HUMAN;
            // Updated Text
            document.getElementById("turn-indicator").innerText = "YOUR TURN";
            document.getElementById("turn-indicator").style.color = "#d4af37"; // Gold
        }
    } catch (error) {
        console.error("AI Error:", error);
    }
}

// ... CheckWinner and EndGame remain the same ...

function checkWinner(player) {
    // Horizontal
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS - 3; c++) {
            if (board[r][c] == player && board[r][c+1] == player && board[r][c+2] == player && board[r][c+3] == player) return true;
        }
    }
    // Vertical
    for (let c = 0; c < COLS; c++) {
        for (let r = 0; r < ROWS - 3; r++) {
            if (board[r][c] == player && board[r+1][c] == player && board[r+2][c] == player && board[r+3][c] == player) return true;
        }
    }
    // Anti-Diagonal
    for (let r = 0; r < ROWS - 3; r++) {
        for (let c = 0; c < COLS - 3; c++) {
            if (board[r][c] == player && board[r+1][c+1] == player && board[r+2][c+2] == player && board[r+3][c+3] == player) return true;
        }
    }
    // Diagonal
    for (let r = 3; r < ROWS; r++) {
        for (let c = 0; c < COLS - 3; c++) {
            if (board[r][c] == player && board[r-1][c+1] == player && board[r-2][c+2] == player && board[r-3][c+3] == player) return true;
        }
    }
    return false;
}

function endGame(message, colorName) {
    gameOver = true;
    document.getElementById("message-modal").classList.remove("hidden");
    const winnerText = document.getElementById("winner-text");
    winnerText.innerText = message;

    // Style modal based on winner
    const header = document.getElementById("winner-header");
    if (colorName === "GOLD") {
        header.innerText = "KNOCKOUT!";
        header.style.color = "#d4af37";
    } else if (colorName === "RED") {
        header.innerText = "DEFEAT";
        header.style.color = "#e74c3c";
    } else {
        header.innerText = "DRAW";
        header.style.color = "white";
    }
}