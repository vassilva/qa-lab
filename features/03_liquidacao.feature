# language: pt
@regressao @settlement
Funcionalidade: Liquidação T+2 dos negócios
  Como câmara de liquidação
  Quero liquidar cada negócio dois dias úteis depois da negociação
  Para trocar títulos e dinheiro na data certa, cumprindo o calendário TARGET2

  Critérios de aceitação:
    AC-L01  Cada negócio gera uma instrução PENDING para T+2 dias úteis (sem contar fins de semana)
    AC-L02  Os dias de fecho TARGET2 (Natal, Páscoa, 1 de janeiro, 1 de maio, 26 de dezembro) não contam
    AC-L03  O fecho do dia (EOD) só liquida as instruções que chegaram à data prevista
    AC-L04  Uma instrução retida (hold) não é liquidada até ser libertada (release)
    AC-L05  Todos os negócios têm instrução de liquidação (reconciliação na base de dados)
    AC-L06  A data de negócio só pode ser um dia útil

  @AC-L01 @AC-L02 @critico
  Esquema do Cenário: Cálculo da data de liquidação T+2
    Dado um mercado limpo com a data de negócio "<negociação>"
    Quando é executado um negócio de 100 "EDP" a 4.50 EUR
    Então é criada uma instrução de liquidação para "<liquidação>" no estado "PENDING"

    Exemplos: Dias úteis normais e fins de semana
      | negociação | liquidação | nota                          |
      | 2026-11-02 | 2026-11-04 | segunda → quarta              |
      | 2026-11-05 | 2026-11-09 | quinta → segunda              |
      | 2026-11-06 | 2026-11-10 | sexta → terça                 |

    Exemplos: Feriados TARGET2
      | negociação | liquidação | nota                          |
      | 2026-12-23 | 2026-12-28 | Natal e 26 de dezembro        |
      | 2027-03-25 | 2027-03-31 | Sexta-feira Santa e Páscoa    |

  @AC-L03 @critico @smoke
  Cenário: A instrução só é liquidada no fecho do dia da data prevista
    Dado um mercado limpo com a data de negócio "2026-11-06"
    E é executado um negócio de 100 "EDP" a 4.50 EUR
    Quando é feito o fecho do dia
    Então a instrução fica no estado "PENDING"
    E a data de negócio passa a ser "2026-11-09"
    Quando é feito o fecho do dia
    Então a instrução fica no estado "PENDING"
    Quando é feito o fecho do dia
    Então a instrução fica liquidada em "2026-11-10"

  @AC-L04 @alto
  Cenário: Uma instrução retida não é liquidada até ser libertada
    Dado um mercado limpo com a data de negócio "2026-11-02"
    E é executado um negócio de 100 "EDP" a 4.50 EUR
    Quando a instrução é retida (hold)
    E são feitos 3 fechos do dia
    Então a instrução fica no estado "ON_HOLD"
    Quando a instrução é libertada (release)
    E é feito o fecho do dia
    Então a instrução fica liquidada em "2026-11-05"

  @AC-L05 @critico
  Cenário: Reconciliação: todos os negócios têm instrução de liquidação
    Dado um mercado limpo com a data de negócio "2026-11-02"
    E que existe uma ordem "V1" de venda de 300 "GALP" a 15.20 EUR
    E que existe uma ordem "C1" de compra de 100 "GALP" a 15.20 EUR
    E que existe uma ordem "C2" de compra de 200 "GALP" a 15.25 EUR
    Então existem 2 negócios
    E todos os negócios têm instrução de liquidação
    E a quantidade executada de cada ordem coincide com os negócios

  @AC-L06 @medio
  Cenário: A data de negócio não pode ser um fim de semana
    Dado um mercado limpo com a data de negócio "2026-11-06"
    Quando se tenta definir a data de negócio "2026-11-07"
    Então o pedido é recusado com o código 400
    E a data de negócio continua a ser "2026-11-06"
