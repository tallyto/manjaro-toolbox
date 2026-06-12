const actionsEl = document.querySelector('#actions')
const packagesEl = document.querySelector('#packages')
const outputEl = document.querySelector('#output')
const statusText = document.querySelector('#status-text')
const statusDot = document.querySelector('#status-dot')
const refreshBtn = document.querySelector('#refresh')
const clearBtn = document.querySelector('#clear')
const passwordInput = document.querySelector('#sudo-password')
const installSelectedBtn = document.querySelector('#install-selected')
const selectRecommendedBtn = document.querySelector('#select-recommended')
const clearSelectionBtn = document.querySelector('#clear-selection')
const togglePasswordBtn = document.querySelector('#toggle-password')

const recommendedPackages = new Set([
  'vlc', 'btop', 'ripgrep', 'bat', 'eza', 'fzf', 'fd', 'dust', 'duf',
  'tldr', 'jq', 'yq', 'httpie', 'pacman-contrib', 'reflector', 'postman-bin'
])

function setStatus(text, state = 'ready') {
  statusText.textContent = text
  statusDot.className = state === 'ready' ? '' : state
}

function dangerLabel(danger) {
  return {
    safe: 'Seguro',
    sudo: 'Usa sudo',
    interactive: 'Interativo',
    destructive: 'Remove pacotes'
  }[danger] || danger
}

function selectedPackages() {
  return Array.from(document.querySelectorAll('[data-package]:checked')).map(input => input.value)
}

function setButtonsDisabled(disabled) {
  for (const button of document.querySelectorAll('button')) button.disabled = disabled
}

async function loadPackages() {
  const res = await fetch('/api/packages')
  const data = await res.json()
  packagesEl.innerHTML = ''

  for (const group of data.groups) {
    const section = document.createElement('article')
    section.className = 'package-group'
    section.innerHTML = `<h3>${group.title}</h3>`

    for (const item of group.packages) {
      const label = document.createElement('label')
      label.className = 'package-item'
      label.innerHTML = `
        <input type="checkbox" data-package value="${item.name}">
        <span>
          <strong>${item.name}${item.source === 'aur' ? ' · AUR' : ''}</strong>
          <small>${item.description}</small>
        </span>
      `
      section.appendChild(label)
    }
    packagesEl.appendChild(section)
  }
}

async function loadActions() {
  setStatus('Carregando ações...', 'busy')
  const res = await fetch('/api/actions')
  const data = await res.json()
  actionsEl.innerHTML = ''

  for (const action of data.actions) {
    const card = document.createElement('article')
    card.className = 'card'
    const warn = ['destructive', 'sudo', 'interactive'].includes(action.danger)
    card.innerHTML = `
      <div>
        <div class="meta">
          <span>${action.category}</span>
          <span class="badge ${action.danger}">${dangerLabel(action.danger)}</span>
        </div>
        <h3>${action.title}</h3>
        <p>${action.description}</p>
      </div>
      <button type="button" class="${warn ? 'warn' : ''}">Executar</button>
    `
    card.querySelector('button').addEventListener('click', () => runAction(action))
    actionsEl.appendChild(card)
  }
  setStatus('Pronto')
}

async function runAction(action) {
  if (action.danger === 'destructive') {
    const ok = confirm(`Executar "${action.title}"? Essa ação pode remover pacotes.`)
    if (!ok) return
  }
  setStatus(`Executando ${action.title}...`, 'busy')
  outputEl.textContent = `Executando: ${action.title}

`
  setButtonsDisabled(true)

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: action.id })
    })
    const data = await res.json()
    outputEl.textContent += data.output || data.error || '(sem saída)'
    setStatus(data.ok ? 'Concluído' : `Finalizado com erro ${data.code ?? ''}`, data.ok ? 'ready' : 'error')
  } catch (err) {
    outputEl.textContent += String(err)
    setStatus('Erro ao executar ação', 'error')
  } finally {
    setButtonsDisabled(false)
  }
}

async function installSelected() {
  const packages = selectedPackages()
  if (packages.length === 0) {
    alert('Selecione pelo menos um pacote.')
    return
  }
  const password = passwordInput.value
  if (!password) {
    const ok = confirm('Sem senha preenchida, o sudo só funciona se já estiver autenticado no terminal. Continuar?')
    if (!ok) return
  }

  setStatus('Instalando pacotes selecionados...', 'busy')
  outputEl.textContent = `Instalando pacotes:
${packages.join(' ')}

`
  setButtonsDisabled(true)

  try {
    const res = await fetch('/api/install-selected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ packages, password })
    })
    const data = await res.json()
    outputEl.textContent += data.output || data.error || '(sem saída)'
    setStatus(data.ok ? 'Instalação concluída' : `Instalação falhou ${data.code ?? ''}`, data.ok ? 'ready' : 'error')
  } catch (err) {
    outputEl.textContent += String(err)
    setStatus('Erro ao instalar pacotes', 'error')
  } finally {
    passwordInput.value = ''
    setButtonsDisabled(false)
  }
}

refreshBtn.addEventListener('click', async () => {
  await loadPackages()
  await loadActions()
})
clearBtn.addEventListener('click', () => { outputEl.textContent = 'Saída limpa.' })
togglePasswordBtn.addEventListener('click', () => {
  const showing = passwordInput.type === 'text'
  passwordInput.type = showing ? 'password' : 'text'
  togglePasswordBtn.textContent = showing ? 'Mostrar' : 'Ocultar'
  togglePasswordBtn.setAttribute('aria-pressed', String(!showing))
  passwordInput.focus()
})
installSelectedBtn.addEventListener('click', installSelected)
selectRecommendedBtn.addEventListener('click', () => {
  for (const input of document.querySelectorAll('[data-package]')) {
    input.checked = recommendedPackages.has(input.value)
  }
})
clearSelectionBtn.addEventListener('click', () => {
  for (const input of document.querySelectorAll('[data-package]')) input.checked = false
})

Promise.all([loadPackages(), loadActions()])
