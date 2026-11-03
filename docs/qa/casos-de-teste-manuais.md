# Casos de teste manuais · QA Lab

Complementam os testes automáticos onde o olho humano acrescenta valor: a página web, a experiência
de uso, a leitura de logs e de relatórios, e verificações em UAT antes do go/no-go.
Executados na página da mini bolsa (QA `localhost:8000` ou UAT `localhost:9000`) e no terminal Linux.

| ID | Título | Critério de aceitação | Automatizado? |
| --- | --- | --- | --- |
| TC-M01 | Negócio aparece no livro, nos negócios e na liquidação | AC-N01, AC-L01 | Parcial (BDD cobre a API, não a página) |
| TC-M02 | Execução parcial visível no livro de ordens | AC-N02 | Parcial |
| TC-M03 | Mensagens de rejeição claras para o utilizador | AC-V01, AC-V02 | Parcial |
| TC-M04 | Cancelar uma ordem a partir do livro | AC-V03 | Não |
| TC-M05 | Fecho do dia na página e relatório CSV no servidor | AC-L03 | Parcial (o CSV não é verificado) |
| TC-M06 | Hold e release a partir da página | AC-L04 | Parcial |
| TC-M07 | Data de negócio: recusar fim de semana e feriado | AC-L06, AC-L02 | Parcial |
| TC-M08 | Consola SQL: reconciliação negócios ↔ instruções | AC-L05 | Sim (BDD) |
| TC-M09 | Selo de ambiente e versão iguais em QA e UAT | OBJ-4 | Parcial (smoke) |
| TC-M10 | Logs com etiqueta de componente permitem seguir uma ordem | Suporte a defeitos | Não |

---

### TC-M01 · Negócio aparece no livro, nos negócios e na liquidação
**Pré-condições:** ambiente QA, botão **Reiniciar ambiente** carregado, símbolo EDP selecionado.

1. Quantidade 100, preço 4.50 → **Vender**.
2. Quantidade 100, preço 4.55 → **Comprar**.

**Esperado:** a venda desaparece do livro; em **Negócios** surge 1 negócio de 100 a **4.50** com a data de negócio;
em **Instruções de liquidação** surge uma instrução `PENDING` com liquidação prevista a T+2 dias úteis; ambas as ordens ficam `FILLED`.

### TC-M02 · Execução parcial visível no livro de ordens
1. Vender 100 EDP a 4.50. 2. Comprar 40 EDP a 4.50.

**Esperado:** no livro de vendas fica a mesma ordem com **60**; a venda fica `PARTIALLY_FILLED` com restante 60; o negócio é de 40.

### TC-M03 · Mensagens de rejeição claras
1. Comprar 10 001 EDP a 4.50. 2. Comprar 100 EDP a 4.505. 3. Comprar 100 EDP a 4.96.

**Esperado:** cada ordem aparece `REJECTED` na tabela de ordens com o motivo (`Quantidade inválida`, `Preço fora do tick size`,
`Preço fora das bandas`); a "Última resposta da API" mostra HTTP 422; nenhuma entra no livro.

### TC-M04 · Cancelar uma ordem a partir do livro
1. Comprar 100 EDP a 4.40. 2. No livro de compras, carregar no ✕ da ordem.

**Esperado:** a ordem sai do livro e fica `CANCELLED`; a resposta da API é HTTP 200. Repetir o ✕ numa ordem já executada (via API)
devolve HTTP 409.

### TC-M05 · Fecho do dia e relatório CSV
1. Executar um negócio (TC-M01). 2. Carregar em **Fechar o dia (EOD)** três vezes (a partir de uma segunda-feira).
3. No terminal Linux: `ls /var/log/qa-lab/eod/` e `cat /var/log/qa-lab/eod/settlement_<data>.csv`.

**Esperado:** a instrução só passa a `SETTLED` no fecho do dia da data prevista; a data de negócio avança sempre para o próximo dia útil;
existe um CSV por fecho, com a instrução e o estado correto.

### TC-M06 · Hold e release
1. Executar um negócio. 2. Na instrução, carregar em **Hold**. 3. Fazer fechos do dia até passar a data prevista.
4. Carregar em **Release** e fazer mais um fecho.

**Esperado:** retida, a instrução não é liquidada (o log regista `NÃO liquidada na data prevista`); depois do release, liquida no fecho seguinte.

### TC-M07 · Data de negócio inválida
1. Definir a data de negócio para um sábado. 2. Para 2026-12-25.

**Esperado:** ambas recusadas (HTTP 400, com mensagem que explica porquê); a data de negócio não muda.

### TC-M08 · Reconciliação na consola SQL
1. Executar vários negócios (incluindo parciais). 2. Correr os presets **Negócios sem instrução (reconciliação)** e
**Quantidade executada vs. ordem**.

**Esperado:** 0 linhas em ambos.

### TC-M09 · Mesmo ambiente, mesma versão
1. Abrir QA e UAT lado a lado depois de um pipeline aprovado.

**Esperado:** selos **QA** (azul) e **UAT** (amarelo) com **a mesma versão**, igual ao nome do build no Jenkins.

### TC-M10 · Seguir uma ordem nos logs
1. Executar TC-M02. 2. No terminal: `grep O00001 /var/log/qa-lab/qa-lab.log`.

**Esperado:** é possível seguir a ordem pelo gateway (`[OEG]`), motor (`[ME]`) e liquidação (`[SETTLEMENT]`), com horas e quantidades coerentes.

---

## Sessão exploratória (charter)

**Missão:** explorar combinações de ordens pouco habituais no Matching Engine durante 30 minutos, para encontrar comportamentos
inesperados no preço, nas quantidades ou na liquidação.

**Ideias:** várias ordens ao mesmo preço e lados alternados; ordens de mercado contra um livro com vários níveis de preço;
cancelar uma ordem parcialmente executada; quantidades e preços nos limites; fecho do dia sem negócios; trocar de símbolo a meio.

**Registo:** notas com hora, o que foi feito, o que se observou, e perguntas ou defeitos. Defeitos → `docs/defeitos/`.

## Registo de execução

| Versão | Ambiente | Data | Executado por | TC-M01 | M02 | M03 | M04 | M05 | M06 | M07 | M08 | M09 | M10 | Defeitos |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.4.0-… | QA | | | | | | | | | | | | | |
| 0.4.0-… | QA (modo desafio) | | | | | | | | | | | | | |

Legenda: ✓ passou · ✗ falhou (indicar o defeito) · — não executado.
