/*******************************************
 * FULL TURN-BASED MOCK MULTIPLAYER (2 ROUNDS)
 *******************************************/

let players = [
    { id: "p1", name: "John", role: "Player" },
    { id: "p2", name: "Alice", role: "Player" },
    { id: "p3", name: "Mike", role: "Imposter" },
    { id: "p4", name: "Sara", role: "Player" }
];

let realWord = "School";

let imposter = players.find(p => p.role === "Imposter");
let civilians = players.filter(p => p.role !== "Imposter");
let turnOrder = [...civilians, imposter];

let clues = { 1: [], 2: [] };

let currentRound = 1;
let maxRounds = 2;

let myIndex = 0;
let myPlayer = turnOrder[myIndex];

// grab elements
const roleText = document.getElementById("roleText");
const assignedWord = document.getElementById("assignedWord");
const timerEl = document.getElementById("roundTimer");
const previousCluesBox = document.getElementById("previousClues");
const clueInput = document.getElementById("clueInput");
const submitBtn = document.getElementById("submitClueBtn");
const clueStatus = document.getElementById("clueStatus");


function renderRoleAndWord() {
    if (myPlayer.role === "Imposter") {
        roleText.innerHTML = `&#127917; You are the IMPOSTER, ${myPlayer.name} &mdash; Blend in&hellip; or be exposed`;
        assignedWord.innerText = "Blend. Trick. Survive.";
    } else {
        roleText.innerHTML = `&#128737; Your turn, ${myPlayer.name} &mdash; Protect the secret word!`;
        assignedWord.innerText = realWord;
    }
}

function renderPreviousClues() {
    previousCluesBox.innerHTML = "";

    for (let r = 1; r <= currentRound; r++) {
        if (clues[r].length === 0) continue;

        const header = document.createElement("p");
        header.style.fontWeight = "bold";
        header.style.marginTop = "12px";
        header.innerText = `Round ${r}`;
        previousCluesBox.appendChild(header);

        clues[r].forEach(c => {
            const row = document.createElement("div");
            row.classList.add("clue-line");

            row.innerHTML = `
                <span class="clue-name">${c.name}</span>
                <span class="clue-word">${c.clue}</span>
            `;

            previousCluesBox.appendChild(row);
        });
    }
}


// ---------------- TIMER ----------------

let timeLeft = 30;
let timer = null;

function updateTimerDisplay(seconds) {
    // Remove previous classes
    timerEl.classList.remove("timer-black", "timer-orange", "timer-red");

    // 30–11: black, 10–6: dark orange, 5–0: red + blink
    if (seconds > 10) {
        timerEl.classList.add("timer-black");
    } else if (seconds > 5) {
        timerEl.classList.add("timer-orange");
    } else {
        timerEl.classList.add("timer-red");
    }

    timerEl.textContent = seconds;
}

function tick() {
    updateTimerDisplay(timeLeft);
    timeLeft--;

    if (timeLeft < 0) {
        clearInterval(timer);
        onClueSubmitted("(no clue)");
    }
}

function startTimer() {
    if (timer) clearInterval(timer);
    updateTimerDisplay(timeLeft);
    timer = setInterval(tick, 1000);
}

// ---------------------------------------

submitBtn.addEventListener("click", () => {
    const clue = clueInput.value.trim();
    if (clue === "") {
        clueStatus.innerText = "Please enter a clue!";
        return;
    }
    onClueSubmitted(clue);
});

function onClueSubmitted(clue) {
    clues[currentRound].push({ name: myPlayer.name, clue });

    clueInput.disabled = true;
    submitBtn.disabled = true;

    clueStatus.innerText = "Clue submitted. Waiting for others...";
    clearInterval(timer);

    setTimeout(() => advanceTurn(), 800);
}

function advanceTurn() {
    if (myIndex === turnOrder.length - 1) {
        if (currentRound === maxRounds) {
            window.location.href = "vote.html";
            return;
        }

        currentRound++;
        myIndex = 0;
        myPlayer = turnOrder[0];

        resetTurnUI();
        return;
    }

    myIndex++;
    myPlayer = turnOrder[myIndex];

    resetTurnUI();
}

function resetTurnUI() {
    clueInput.disabled = false;
    clueInput.value = "";
    submitBtn.disabled = false;
    clueStatus.innerText = "";

    timeLeft = 30;

    renderRoleAndWord();
    renderPreviousClues();

    startTimer();
}

// INIT
renderRoleAndWord();
renderPreviousClues();
startTimer();
