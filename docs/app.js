(() => {
  let teamsData = null;
  let selectedTeams = new Set();
  let activeSport = null;
  let activeLeague = null;

  const sportTabs = document.getElementById("sport-tabs");
  const leagueTabs = document.getElementById("league-tabs");
  const teamGrid = document.getElementById("team-grid");
  const selectedSection = document.getElementById("selected-section");
  const selectedTeamsEl = document.getElementById("selected-teams");
  const selectedCount = document.getElementById("selected-count");
  const teamsInput = document.getElementById("teams-input");
  const submitBtn = document.getElementById("submit-btn");
  const form = document.getElementById("subscribe-form");
  const formStatus = document.getElementById("form-status");

  async function init() {
    try {
      const resp = await fetch("teams.json");
      teamsData = await resp.json();
      renderSportTabs();
      selectSport(0);
    } catch (e) {
      teamGrid.innerHTML = "<p>Failed to load teams. Please refresh.</p>";
    }
  }

  function renderSportTabs() {
    sportTabs.innerHTML = "";
    teamsData.sports.forEach((sport, i) => {
      const tab = document.createElement("button");
      tab.className = "tab";
      tab.textContent = sport.name;
      tab.addEventListener("click", () => selectSport(i));
      sportTabs.appendChild(tab);
    });
  }

  function selectSport(index) {
    activeSport = index;
    document.querySelectorAll("#sport-tabs .tab").forEach((t, i) => {
      t.classList.toggle("active", i === index);
    });
    renderLeagueTabs();
    selectLeague(0);
  }

  function renderLeagueTabs() {
    leagueTabs.innerHTML = "";
    const leagues = teamsData.sports[activeSport].leagues;
    leagues.forEach((league, i) => {
      const tab = document.createElement("button");
      tab.className = "tab";
      if (league.logo_url) {
        tab.classList.add("tab-logo");
        const img = document.createElement("img");
        img.src = league.logo_url;
        img.alt = league.name;
        img.title = league.name;
        img.className = "league-logo";
        img.onerror = function () {
          this.remove();
          tab.textContent = league.name;
          tab.classList.remove("tab-logo");
        };
        tab.appendChild(img);
      } else {
        tab.textContent = league.name;
      }
      tab.addEventListener("click", () => selectLeague(i));
      leagueTabs.appendChild(tab);
    });
  }

  function selectLeague(index) {
    activeLeague = index;
    document.querySelectorAll("#league-tabs .tab").forEach((t, i) => {
      t.classList.toggle("active", i === index);
    });
    renderTeams();
  }

  function renderTeams() {
    teamGrid.innerHTML = "";
    const teams = [...teamsData.sports[activeSport].leagues[activeLeague].teams]
      .sort((a, b) => a.name.localeCompare(b.name));
    teams.forEach(team => {
      const card = document.createElement("div");
      card.className = "team-card" + (selectedTeams.has(team.id) ? " selected" : "");
      card.style.backgroundColor = team.primary_color;
      card.style.color = team.text_color;

      const label = document.createElement("span");
      label.className = "team-label";
      label.textContent = team.short_name;

      if (team.logo_url) {
        const img = document.createElement("img");
        img.src = team.logo_url;
        img.alt = team.short_name;
        img.className = "team-logo";
        img.loading = "lazy";
        img.onerror = function () {
          this.style.display = "none";
          label.classList.add("no-logo");
        };
        card.appendChild(img);
      } else {
        label.classList.add("no-logo");
      }

      card.appendChild(label);
      card.addEventListener("click", () => toggleTeam(team));
      teamGrid.appendChild(card);
    });
  }

  function toggleTeam(team) {
    if (selectedTeams.has(team.id)) {
      selectedTeams.delete(team.id);
    } else {
      selectedTeams.add(team.id);
    }
    renderTeams();
    renderSelected();
    updateForm();
  }

  function findTeam(id) {
    for (const sport of teamsData.sports) {
      for (const league of sport.leagues) {
        const t = league.teams.find(t => t.id === id);
        if (t) return t;
      }
    }
    return null;
  }

  function renderSelected() {
    if (selectedTeams.size === 0) {
      selectedSection.style.display = "none";
      return;
    }
    selectedSection.style.display = "block";
    selectedCount.textContent = "(" + selectedTeams.size + ")";
    selectedTeamsEl.innerHTML = "";
    selectedTeams.forEach(id => {
      const team = findTeam(id);
      if (!team) return;
      const chip = document.createElement("span");
      chip.className = "selected-chip";
      chip.style.backgroundColor = team.primary_color;
      chip.style.color = team.text_color;
      const logoHtml = team.logo_url
        ? '<img src="' + team.logo_url + '" alt="" class="chip-logo">'
        : '';
      chip.innerHTML = logoHtml + team.short_name + ' <span class="remove">&times;</span>';
      chip.querySelector(".remove").addEventListener("click", () => toggleTeam(team));
      selectedTeamsEl.appendChild(chip);
    });
  }

  function updateForm() {
    teamsInput.value = Array.from(selectedTeams).join(",");
    submitBtn.disabled = selectedTeams.size === 0;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    formStatus.textContent = "Subscribing...";
    formStatus.className = "";

    const data = new FormData(form);
    try {
      const resp = await fetch(form.action, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" }
      });
      if (resp.ok) {
        formStatus.textContent = "You're subscribed! Check your inbox soon.";
        formStatus.className = "status-success";
        form.reset();
        selectedTeams.clear();
        renderTeams();
        renderSelected();
        updateForm();
      } else {
        throw new Error("Submission failed");
      }
    } catch {
      formStatus.textContent = "Something went wrong. Please try again.";
      formStatus.className = "status-error";
      submitBtn.disabled = false;
    }
  });

  init();
})();
