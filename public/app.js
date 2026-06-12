const actionsEl = document.querySelector('#actions')
const outputEl = document.querySelector('#output')
const statusText = document.querySelector('#status-text')
const statusDot = document.querySelector('#status-dot')
const refreshBtn = document.querySelector('#refresh')
const clearBtn = document.querySelector('#clear')

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
  for (const button of document.querySelectorAll('button')) button.disabled = true

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
    for (const button of document.querySelectorAll('button')) button.disabled = false
  }
}

refreshBtn.addEventListener('click', loadActions)
clearBtn.addEventListener('click', () => { outputEl.textContent = 'Saída limpa.' })
loadActions()
