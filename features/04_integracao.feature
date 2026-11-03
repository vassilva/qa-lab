# language: pt
@regressao @integracao
Funcionalidade: Integração entre o Trading, o Settlement e o T2S
  Como equipa de pós-negociação
  Quero que cada negócio chegue ao Settlement uma e uma só vez, e seja liquidado no T2S
  Para que os dois sistemas estejam sempre reconciliados, mesmo quando há falhas

  Critérios de aceitação:
    AC-I01  Cada negócio publica um evento TradeExecuted que respeita o contrato v1
    AC-I02  Um evento entregue duas vezes não cria uma segunda instrução (idempotência)
    AC-I03  Uma mensagem que não respeita o contrato vai para a fila de erros e não cria instrução
    AC-I04  Se o Settlement estiver indisponível, a negociação continua e as instruções chegam quando ele recupera
    AC-I05  Uma instrução rejeitada pelo T2S fica FAILED com o motivo e é reciclada no fecho seguinte
    AC-I06  Se o T2S estiver indisponível, nada é liquidado e as instruções liquidam quando ele volta

  Contexto:
    Dado um mercado limpo com a data de negócio "2026-11-02"

  @AC-I01 @critico @smoke
  Cenário: O negócio chega ao Settlement com os mesmos dados
    Quando é executado um negócio de 100 "EDP" a 4.50 EUR
    Então o evento publicado respeita o contrato TradeExecuted v1
    E é criada uma instrução de liquidação para "2026-11-04" no estado "PENDING"
    E a reconciliação entre o Trading e o Settlement não tem diferenças

  @AC-I02 @critico
  Cenário: Evento duplicado não cria uma segunda instrução
    Dado é executado um negócio de 100 "EDP" a 4.50 EUR
    Quando o evento do negócio é entregue outra vez
    Então o negócio continua a ter uma única instrução de liquidação

  @AC-I03 @alto
  Cenário: Mensagem fora do contrato vai para a fila de erros
    Quando é publicada uma mensagem com a quantidade 0 e sem identificador do evento
    Então a mensagem aparece nos eventos rejeitados do Settlement
    E não existe nenhuma instrução de liquidação

  @AC-I04 @critico
  Cenário: Settlement indisponível: a negociação continua e as instruções chegam depois
    Dado que o Settlement deixou de consumir eventos
    Quando é executado um negócio de 100 "GALP" a 15.20 EUR sem esperar pelo Settlement
    Então a reconciliação mostra o negócio em falta no Settlement
    Quando o Settlement volta a consumir eventos
    Então a reconciliação entre o Trading e o Settlement não tem diferenças

  @AC-I05 @alto
  Cenário: Rejeição pelo T2S e reciclagem no fecho seguinte
    Dado é executado um negócio de 100 "EDP" a 4.50 EUR
    E o T2S rejeita as instruções de "EDP"
    Quando são feitos 3 fechos do dia
    Então a instrução fica no estado "FAILED"
    Quando o T2S volta ao normal
    E é feito o fecho do dia
    Então a instrução fica liquidada em "2026-11-05"

  @AC-I06 @alto
  Cenário: T2S indisponível no fecho do dia
    Dado é executado um negócio de 100 "NOS" a 3.80 EUR
    E o T2S está indisponível
    Quando são feitos 3 fechos do dia
    Então a instrução fica no estado "FAILED"
    Quando o T2S volta ao normal
    E é feito o fecho do dia
    Então a instrução fica liquidada em "2026-11-05"
