# language: pt
@regressao @matching
Funcionalidade: Execução de ordens no Matching Engine
  Como participante de mercado
  Quero que as minhas ordens sejam cruzadas pela regra preço-tempo
  Para ter execuções justas e previsíveis

  Critérios de aceitação:
    AC-N01  O negócio é feito ao preço da ordem que já estava no livro
    AC-N02  Numa execução parcial, a quantidade por executar fica no livro
    AC-N03  Com o mesmo preço, executa primeiro a ordem que chegou antes
    AC-N04  Uma ordem que não cruza fica no livro e não gera negócio
    AC-N05  Uma ordem de mercado sem contraparte é cancelada e não fica no livro

  Contexto:
    Dado um mercado limpo com a data de negócio "2026-11-02"

  @AC-N01 @critico @smoke
  Cenário: Compra que cruza executa ao preço da venda que estava no livro
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.50 EUR
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a 4.55 EUR
    Então a ordem "C1" fica no estado "FILLED"
    E existe 1 negócio de 100 ações a 4.50 EUR
    E o livro de vendas de "EDP" fica vazio

  @AC-N02 @critico
  Cenário: Execução parcial deixa o restante no livro
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.50 EUR
    Quando é submetida uma ordem "C1" de compra de 40 "EDP" a 4.50 EUR
    Então a ordem "C1" fica no estado "FILLED"
    E a ordem "V1" fica no estado "PARTIALLY_FILLED" com 60 por executar

  @AC-N03 @critico
  Cenário: Com o mesmo preço, executa primeiro quem chegou antes
    Dado que existe uma ordem "C1" de compra de 100 "EDP" a 4.48 EUR
    E que existe uma ordem "C2" de compra de 100 "EDP" a 4.48 EUR
    Quando é submetida uma ordem "V1" de venda de 100 "EDP" a 4.48 EUR
    Então a ordem "C1" fica no estado "FILLED"
    E a ordem "C2" fica no estado "NEW"

  @AC-N03 @critico
  Cenário: O melhor preço tem prioridade sobre a ordem de chegada
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.52 EUR
    E que existe uma ordem "V2" de venda de 100 "EDP" a 4.51 EUR
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a 4.55 EUR
    Então a ordem "V2" fica no estado "FILLED"
    E a ordem "V1" fica no estado "NEW"
    E existe 1 negócio de 100 ações a 4.51 EUR

  @AC-N04 @alto
  Cenário: Ordem que não cruza fica no livro
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.52 EUR
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a 4.50 EUR
    Então a ordem "C1" fica no estado "NEW"
    E não existe nenhum negócio

  @AC-N05 @alto
  Cenário: Ordem de mercado sem contraparte é cancelada
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a mercado
    Então a ordem "C1" fica no estado "CANCELLED"
    E o livro de compras de "EDP" fica vazio
