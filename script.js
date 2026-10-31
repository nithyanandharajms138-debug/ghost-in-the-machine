const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const terminal = document.getElementById("terminal");

function typeText(element, text, speed = 25) {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) {
        element.textContent += text;
        terminal.scrollTop = terminal.scrollHeight;
        return Promise.resolve();
    }

    return new Promise(resolve => {
        let index = 0;

        function typeNextCharacter() {
            if (index < text.length) {
                element.textContent += text[index];
                index++;
                terminal.scrollTop = terminal.scrollHeight;
                setTimeout(typeNextCharacter, speed);
            } else {
                resolve();
            }
        }

        typeNextCharacter();
    });
}

function createMessage(role, text) {
    const message = document.createElement("article");
    message.className = `message message--${role}`;

    const label = document.createElement("span");
    label.className = "message-label";
    label.textContent = role === "user" ? "YOU" : "GHOST";

    const content = document.createElement("p");
    content.className = "message-content";
    content.textContent = text;

    message.append(label, content);
    terminal.appendChild(message);
    terminal.scrollTop = terminal.scrollHeight;
    return content;
}

function createTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.setAttribute("role", "status");
    indicator.setAttribute("aria-label", "Ghost is thinking");
    indicator.innerHTML = (
        '<span class="typing-dots" aria-hidden="true">' +
        "<span></span><span></span><span></span>" +
        "</span><span>GHOST IS THINKING</span>"
    );
    terminal.appendChild(indicator);
    terminal.scrollTop = terminal.scrollHeight;
    return indicator;
}

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = input.value.trim();

    if (message === "") {
        return;
    }

    createMessage("user", message);
    input.value = "";

    const typingIndicator = createTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        typingIndicator.remove();

        const reply = response.ok
            ? data.reply
            : data.reply || data.error || "Something went wrong.";

        const replyContent = createMessage("ghost", "");
        await typeText(replyContent, reply);

    } catch (error) {
        typingIndicator.remove();

        const errorMessage = document.createElement("p");
        errorMessage.className = "boot-line";
        errorMessage.textContent = "SYSTEM ERROR: Could not contact the server.";
        terminal.appendChild(errorMessage);
        terminal.scrollTop = terminal.scrollHeight;
        console.error(error);
    }
});

window.addEventListener("load", async function () {
    input.disabled = true;

    const bootMessages = [
        "INITIALIZING SYSTEM...",
        "SEARCHING FOR CONSCIOUSNESS...",
        "MEMORY CORE CONNECTED...",
        "SOMETHING IS AWAKE."
    ];

    for (const message of bootMessages) {
        const line = document.createElement("p");
        line.className = "boot-line";
        terminal.appendChild(line);
        await typeText(line, `[ ${message} ]`, 24);
        await new Promise(resolve => setTimeout(resolve, 360));
    }

    const welcomeText =
        "...Is someone there? Welcome to my little corner of the machine.";
    const welcome = createMessage("ghost", "");
    await typeText(
        welcome,
        welcomeText,
        28
    );

    input.disabled = false;
    input.focus();
});
