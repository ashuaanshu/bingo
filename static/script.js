const socket = io();

// State
let mySid = null;
let myTurn = false;
let gameActive = false;

// DOM Elements
const loginScreen = document.getElementById("login-screen");
const gameScreen = document.getElementById("game-screen");
const usernameInput = document.getElementById("username");
const joinBtn = document.getElementById("join-btn");
const errorMsg = document.getElementById("error-msg");
const boardEl = document.getElementById("board");
const turnIndicator = document.getElementById("turn-indicator");
const playerNameEl = document.getElementById("player-name");
const opponentNameEl = document.getElementById("opponent-name");
const myLinesEl = document.getElementById("my-lines");
const oppLinesEl = document.getElementById("opp-lines");
const winnerModal = document.getElementById("winner-modal");
const winnerText = document.getElementById("winner-text");
const resetBtn = document.getElementById("reset-btn");

// --- Event Listeners ---

joinBtn.addEventListener("click", () => {
  const name = usernameInput.value.trim();
  if (!name) return;
  socket.emit("join_game", { name: name });
});

function requestReset() {
  socket.emit("reset_game");
  // Hide modal immediately for UX, actual reset comes from server
  winnerModal.classList.add("hidden");
}

// --- Socket Events ---

socket.on("connect", () => {
  console.log("Connected to server");
});

socket.on("player_joined", (data) => {
  // data.players is list of {name, sid}
  // If I am in the list, fine.
  // If opponent joins, update opponent name text
  // We'll handle this more specifically in game_start
  console.log("Players update:", data.players);
});

socket.on("game_start", (data) => {
  // data: { board: [1..25], opponent: 'Bob', turn: 'sid...', your_sid: '...' }
  mySid = data.your_sid;

  // Switch screens
  loginScreen.classList.add("hidden");
  gameScreen.classList.remove("hidden");

  // Setup Info
  playerNameEl.textContent = usernameInput.value; // Or keep from server?
  if (data.opponent) {
    opponentNameEl.textContent = data.opponent;
  }

  // Render Board
  renderBoard(data.board);

  // Update Turn
  updateTurn(data.turn);

  // Reset scores
  myLinesEl.textContent = "0";
  oppLinesEl.textContent = "0";

  gameActive = true;
  winnerModal.classList.add("hidden");
  resetBtn.classList.remove("hidden");
});

socket.on("number_marked", (data) => {
  // data: { number: 5, turn: 'next_sid', marked_numbers: [...] }
  const number = data.number;

  // Find cell and mark it
  const cells = document.querySelectorAll(".bingo-cell");
  cells.forEach((cell) => {
    if (parseInt(cell.dataset.number) === number) {
      cell.classList.add("marked");
      cell.classList.remove("bg-blue-100", "hover:bg-blue-200"); // Remove active styles
    }
  });

  updateTurn(data.turn);
});

socket.on("score_update", (data) => {
  myLinesEl.textContent = data.your_lines;
  oppLinesEl.textContent = data.opponent_lines;
});

socket.on("game_over", (data) => {
  gameActive = false;
  winnerModal.classList.remove("hidden");
  if (data.winner === usernameInput.value) {
    // Basic check, ideally use ID
    winnerText.textContent = "You Won! 🎉";
    winnerText.parentElement.classList.add("border-green-500");
  } else {
    winnerText.textContent = `${data.winner} Won! 😢`;
  }
});

socket.on("error_message", (data) => {
  errorMsg.textContent = data.msg;
  errorMsg.classList.remove("hidden");
  setTimeout(() => errorMsg.classList.add("hidden"), 3000);
});

socket.on("player_left", (data) => {
  // Reset UI or Show message
  alert(`${data.name} left the game. The game will reset.`);
  location.reload(); // Simple reload to get back to login
});

// --- Helpers ---

function renderBoard(numbers) {
  boardEl.innerHTML = "";
  numbers.forEach((num) => {
    const cell = document.createElement("div");
    cell.className =
      "bingo-cell bg-blue-100 text-blue-800 font-bold text-xl flex items-center justify-center aspect-square rounded-lg shadow-sm hover:bg-blue-200 select-none";
    cell.textContent = num;
    cell.dataset.number = num;

    cell.addEventListener("click", () => {
      if (!gameActive) return;
      if (!myTurn) {
        showToast("Not your turn!");
        return;
      }
      if (cell.classList.contains("marked")) return;

      socket.emit("make_move", { number: num });
    });

    boardEl.appendChild(cell);
  });
}

function updateTurn(turnSid) {
  if (turnSid === mySid) {
    myTurn = true;
    turnIndicator.textContent = "Your Turn";
    turnIndicator.className =
      "mb-6 p-3 rounded-lg text-center font-bold text-lg bg-green-100 text-green-700 border-2 border-green-400";
    boardEl.classList.add("my-turn");
  } else {
    myTurn = false;
    turnIndicator.textContent = "Opponent's Turn";
    turnIndicator.className =
      "mb-6 p-3 rounded-lg text-center font-bold text-lg bg-red-100 text-red-700";
    boardEl.classList.remove("my-turn");
  }
}

function showToast(msg) {
  // Simple toast or reuse error msg
  const toast = document.createElement("div");
  toast.className =
    "fixed bottom-10 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-6 py-3 rounded-full shadow-lg z-50 animate-fade-in-up";
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}
