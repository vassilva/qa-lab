# language: pt
@regressao @gateway
Funcionalidade: Validação de ordens no Order Entry Gateway
  Como bolsa
  Quero rejeitar ordens inválidas antes de chegarem ao livro de ordens
  Para proteger o mercado de erros dos participantes

  Critérios de aceitação:
    AC-V01  A quantidade tem de estar entre 1 e 10 000 (inclusive)
    AC-V02  O preço tem de ser positivo, múltiplo de 0.01 e estar a ±10% do preço de referência (limites aceites)
    AC-V03  Uma ordem já totalmente executada não pode ser cancelada
    AC-V04  Só são aceites símbolos conhecidos

  Contexto:
    Dado um mercado limpo com a data de negócio "2026-11-02"

  @AC-V01 @alto @fronteira
  Esquema do Cenário: Limites de quantidade
    Quando é submetida uma ordem "C1" de compra de <quantidade> "EDP" a 4.50 EUR
    Então a ordem "C1" fica no estado "<estado>"

    Exemplos:
      | quantidade | estado   |
      | 0          | REJECTED |
      | 1          | NEW      |
      | 10000      | NEW      |
      | 10001      | REJECTED |

  @AC-V02 @alto
  Esquema do Cenário: Rejeição por preço inválido
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a <preço> EUR
    Então a ordem "C1" é rejeitada com o motivo "<motivo>"

    Exemplos:
      | preço | motivo                  |
      | 4.505 | Preço fora do tick size |
      | 4.96  | Preço fora das bandas   |
      | 4.04  | Preço fora das bandas   |
      | 0     | Preço inválido          |

  @AC-V02 @alto @fronteira
  Esquema do Cenário: Os limites das bandas de preço são aceites
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a <preço> EUR
    Então a ordem "C1" fica no estado "NEW"

    Exemplos:
      | preço |
      | 4.05  |
      | 4.95  |

  @AC-V03 @medio
  Cenário: Uma ordem já executada não pode ser cancelada
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.50 EUR
    E que existe uma ordem "C1" de compra de 100 "EDP" a 4.50 EUR
    Quando o participante tenta cancelar a ordem "V1"
    Então o cancelamento é recusado

  @AC-V04 @medio
  Cenário: Símbolo desconhecido é rejeitado
    Quando é submetida uma ordem "C1" de compra de 100 "XPTO" a 4.50 EUR
    Então a ordem "C1" é rejeitada com o motivo "Símbolo desconhecido"
