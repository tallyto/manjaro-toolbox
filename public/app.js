const actionsEl = document.querySelector('#actions')
const packagesEl = document.querySelector('#packages')
const uninstallPackagesEl = document.querySelector('#uninstall-packages')
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
const uninstallSelectedBtn = document.querySelector('#uninstall-selected')
const copyInstallToUninstallBtn = document.querySelector('#copy-install-to-uninstall')
const clearUninstallSelectionBtn = document.querySelector('#clear-uninstall-selection')
const installCountEl = document.querySelector('#install-count')
const uninstallCountEl = document.querySelector('#uninstall-count')

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

function selectedUninstallPackages() {
  return Array.from(document.querySelectorAll('[data-uninstall-package]:checked')).map(input => input.value)
}

function updateCounts() {
  const n = selectedPackages().length
  const u = selectedUninstallPackages().length
  installCountEl.textContent = n > 0 ? n : ''
  uninstallCountEl.textContent = u > 0 ? u : ''
}

function setButtonsDisabled(disabled) {
  for (const button of document.querySelectorAll('button')) button.disabled = disabled
}

function appendOutput(text) {
  outputEl.textContent += text
  outputEl.scrollTop = outputEl.scrollHeight
}

function renderPackageGroups(container, groups, mode) {
  container.innerHTML = ''
  for (const group of groups) {
    const section = document.createElement('article')
    section.className = 'package-group'
    section.innerHTML = `<h3>${group.title}</h3>`

    for (const item of group.packages) {
      const attr = mode === 'uninstall' ? 'data-uninstall-package' : 'data-package'
      const label = document.createElement('label')
      label.className = 'package-item'
      label.innerHTML = `
        <input type="checkbox" ${attr} value="${item.name}">
        <span>
          <strong>${item.name}${item.source === 'aur' ? ' · AUR' : ''}</strong>
          <small>${item.description}</small>
        </span>
      `
      section.appendChild(label)
    }
    container.appendChild(section)
  }
}

async function loadPackages() {
  const res = await fetch('/api/packages')
  const data = await res.json()
  renderPackageGroups(packagesEl, data.groups, 'install')
  renderPackageGroups(uninstallPackagesEl, data.groups, 'uninstall')
  updateCounts()
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
  outputEl.textContent = `Executando: ${action.title}\n\n`
  setButtonsDisabled(true)

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: action.id })
    })
    const data = await res.json()
    appendOutput(data.output || data.error || '(sem saída)')
    setStatus(data.ok ? 'Concluído' : `Finalizado com erro ${data.code ?? ''}`, data.ok ? 'ready' : 'error')
  } catch (err) {
    appendOutput(String(err))
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
  outputEl.textContent = `Instalando pacotes:\n${packages.join(' ')}\n\n`
  setButtonsDisabled(true)

  try {
    const res = await fetch('/api/install-selected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ packages, password })
    })
    const data = await res.json()
    appendOutput(data.output || data.error || '(sem saída)')
    setStatus(data.ok ? 'Instalação concluída' : `Instalação falhou ${data.code ?? ''}`, data.ok ? 'ready' : 'error')
  } catch (err) {
    appendOutput(String(err))
    setStatus('Erro ao instalar pacotes', 'error')
  } finally {
    passwordInput.value = ''
    setButtonsDisabled(false)
  }
}

async function uninstallSelected() {
  const packages = selectedUninstallPackages()
  if (packages.length === 0) {
    alert('Selecione pelo menos um pacote para desinstalar.')
    return
  }
  const ok = confirm(`Desinstalar estes pacotes e dependências não utilizadas?\n\n${packages.join(' ')}`)
  if (!ok) return

  const password = passwordInput.value
  if (!password) {
    const continueWithoutPassword = confirm('Sem senha preenchida, o sudo só funciona se já estiver autenticado no terminal. Continuar?')
    if (!continueWithoutPassword) return
  }

  setStatus('Desinstalando pacotes selecionados...', 'busy')
  outputEl.textContent = `Desinstalando pacotes:\n${packages.join(' ')}\n\n`
  setButtonsDisabled(true)

  try {
    const res = await fetch('/api/uninstall-selected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ packages, password })
    })
    const data = await res.json()
    appendOutput(data.output || data.error || '(sem saída)')
    setStatus(data.ok ? 'Desinstalação concluída' : `Desinstalação falhou ${data.code ?? ''}`, data.ok ? 'ready' : 'error')
  } catch (err) {
    appendOutput(String(err))
    setStatus('Erro ao desinstalar pacotes', 'error')
  } finally {
    passwordInput.value = ''
    setButtonsDisabled(false)
  }
}

packagesEl.addEventListener('change', updateCounts)
uninstallPackagesEl.addEventListener('change', updateCounts)

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
uninstallSelectedBtn.addEventListener('click', uninstallSelected)
selectRecommendedBtn.addEventListener('click', () => {
  for (const input of document.querySelectorAll('[data-package]')) {
    input.checked = recommendedPackages.has(input.value)
  }
  updateCounts()
})
clearSelectionBtn.addEventListener('click', () => {
  for (const input of document.querySelectorAll('[data-package]')) input.checked = false
  updateCounts()
})
copyInstallToUninstallBtn.addEventListener('click', () => {
  const selected = new Set(selectedPackages())
  for (const input of document.querySelectorAll('[data-uninstall-package]')) {
    input.checked = selected.has(input.value)
  }
  updateCounts()
})
clearUninstallSelectionBtn.addEventListener('click', () => {
  for (const input of document.querySelectorAll('[data-uninstall-package]')) input.checked = false
  updateCounts()
})

Promise.all([loadPackages(), loadActions()])
