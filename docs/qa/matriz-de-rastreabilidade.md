# Matriz de rastreabilidade · QA Lab

Gerada automaticamente por `scripts/rastreabilidade.py` em 2026-11-03. Não editar à mão.

| Critério de aceitação | Riscos | Cenários BDD | Casos manuais | Defeitos |
| --- | --- | --- | --- | --- |
| **AC-V01** A quantidade tem de estar entre 1 e 10 000 (inclusive) | R-07 (Alta) | Limites de quantidade (`features/01_validacao_ordens.feature:18`) | TC-M03 | DEF-001 (Aberto (modo desafio)) |
| **AC-V02** O preço tem de ser positivo, múltiplo de 0.01 e estar a ±10% do preço de referência (limites aceites) | R-08 (Alta) | Rejeição por preço inválido (`features/01_validacao_ordens.feature:30`)<br>Os limites das bandas de preço são aceites (`features/01_validacao_ordens.feature:42`) | TC-M03 | — |
| **AC-V03** Uma ordem já totalmente executada não pode ser cancelada | R-12 (Média) | Uma ordem já executada não pode ser cancelada (`features/01_validacao_ordens.feature:52`) | TC-M04 | — |
| **AC-V04** Só são aceites símbolos conhecidos | — | Símbolo desconhecido é rejeitado (`features/01_validacao_ordens.feature:59`) | — | — |
| **AC-N01** O negócio é feito ao preço da ordem que já estava no livro | R-01 (Crítica) | Compra que cruza executa ao preço da venda que estava no livro (`features/02_execucao_ordens.feature:19`) | TC-M01 | DEF-002 (Aberto (modo desafio)) |
| **AC-N02** Numa execução parcial, a quantidade por executar fica no livro | R-04 (Crítica) | Execução parcial deixa o restante no livro (`features/02_execucao_ordens.feature:27`) | TC-M02 | DEF-003 (Aberto (modo desafio)) |
| **AC-N03** Com o mesmo preço, executa primeiro a ordem que chegou antes | R-02 (Crítica) | Com o mesmo preço, executa primeiro quem chegou antes (`features/02_execucao_ordens.feature:34`)<br>O melhor preço tem prioridade sobre a ordem de chegada (`features/02_execucao_ordens.feature:42`) | — | DEF-004 (Aberto (modo desafio)) |
| **AC-N04** Uma ordem que não cruza fica no livro e não gera negócio | R-11 (Alta) | Ordem que não cruza fica no livro (`features/02_execucao_ordens.feature:51`) | — | — |
| **AC-N05** Uma ordem de mercado sem contraparte é cancelada e não fica no livro | R-10 (Alta) | Ordem de mercado sem contraparte é cancelada (`features/02_execucao_ordens.feature:58`) | — | — |
| **AC-L01** Cada negócio gera uma instrução PENDING para T+2 dias úteis (sem contar fins de semana) | R-03 (Crítica) | Cálculo da data de liquidação T+2 (`features/03_liquidacao.feature:17`) | TC-M01 | — |
| **AC-L02** Os dias de fecho TARGET2 (Natal, Páscoa, 1 de janeiro, 1 de maio, 26 de dezembro) não contam | R-03 (Crítica) | Cálculo da data de liquidação T+2 (`features/03_liquidacao.feature:17`) | TC-M07 | DEF-005 (Aberto (modo desafio)) |
| **AC-L03** O fecho do dia (EOD) só liquida as instruções que chegaram à data prevista | R-06 (Crítica) | A instrução só é liquidada no fecho do dia da data prevista (`features/03_liquidacao.feature:34`) | TC-M05 | — |
| **AC-L04** Uma instrução retida (hold) não é liquidada até ser libertada (release) | R-09 (Alta) | Uma instrução retida não é liquidada até ser libertada (`features/03_liquidacao.feature:46`) | TC-M06 | — |
| **AC-L05** Todos os negócios têm instrução de liquidação (reconciliação na base de dados) | R-05 (Crítica) | Reconciliação: todos os negócios têm instrução de liquidação (`features/03_liquidacao.feature:57`) | TC-M08 | DEF-003 (Aberto (modo desafio)), DEF-010 (Fechado) |
| **AC-L06** A data de negócio só pode ser um dia útil | R-13 (Média) | A data de negócio não pode ser um fim de semana (`features/03_liquidacao.feature:67`) | TC-M07 | DEF-005 (Aberto (modo desafio)) |
| **AC-I01** Cada negócio publica um evento TradeExecuted que respeita o contrato v1 | R-14 (Crítica) | O negócio chega ao Settlement com os mesmos dados (`features/04_integracao.feature:20`) | — | — |
| **AC-I02** Um evento entregue duas vezes não cria uma segunda instrução (idempotência) | R-15 (Crítica) | Evento duplicado não cria uma segunda instrução (`features/04_integracao.feature:27`) | — | — |
| **AC-I03** Uma mensagem que não respeita o contrato vai para a fila de erros e não cria instrução | R-17 (Alta) | Mensagem fora do contrato vai para a fila de erros (`features/04_integracao.feature:33`) | — | — |
| **AC-I04** Se o Settlement estiver indisponível, a negociação continua e as instruções chegam quando ele recupera | R-16 (Crítica) | Settlement indisponível: a negociação continua e as instruções chegam depois (`features/04_integracao.feature:39`) | — | — |
| **AC-I05** Uma instrução rejeitada pelo T2S fica FAILED com o motivo e é reciclada no fecho seguinte | R-18 (Alta) | Rejeição pelo T2S e reciclagem no fecho seguinte (`features/04_integracao.feature:47`) | — | — |
| **AC-I06** Se o T2S estiver indisponível, nada é liquidado e as instruções liquidam quando ele volta | R-19 (Alta) | T2S indisponível no fecho do dia (`features/04_integracao.feature:57`) | — | — |

## Cobertura

- Critérios de aceitação: **21**, com cenário automatizado: **21** (100%).
- Riscos de negócio cobertos por critérios com cenário: **19 de 19**.
- Casos manuais: **10** · Defeitos registados: **11**.
