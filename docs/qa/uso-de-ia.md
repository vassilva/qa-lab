# Uso de ferramentas de IA no QA · QA Lab

Este laboratório foi construído com apoio de um assistente de IA (Claude). O registo abaixo mostra **onde** a IA ajudou,
**o que** foi validado por mim e **que regras** sigo. A responsabilidade pelo resultado é sempre humana.

## Onde a IA foi usada

| Atividade (requisito da vaga) | Exemplo neste projeto | Como foi validado |
| --- | --- | --- |
| Desenho de testes | Propostas de valores-fronteira (10 000 / 10 001, bandas 4.05 / 4.95) e de datas de feriados (Natal, Páscoa 2027) | Confirmados contra as regras do README e o calendário TARGET2; testes a correr |
| Geração de casos de teste | Primeira versão dos cenários Gherkin a partir dos critérios de aceitação | Revistos um a um; cada cenário corre no QA e falha quando o defeito existe (modo desafio) |
| Análise de defeitos | Leitura de logs longos do Jenkins (ex.: DEF-008, a comparação de horas que revelou a condição de corrida) | Confirmado com `python3 --version` no contentor e com um novo build |
| Documentação | Estrutura da estratégia de testes, da matriz de risco e dos bug reports | Revistos e ajustados à realidade do projeto |
| Reporting | Gerador do relatório HTML e da matriz de rastreabilidade | Saídas comparadas com os resultados reais do Jenkins |
| Desenvolvimento de automação | Passos behave, scripts Shell e Python | Executados localmente e no pipeline antes de qualquer commit |
| Descoberta de conhecimento | Arquitetura pública da Euronext (Optiq, Euronext Clearing, T2S) como inspiração | Fontes oficiais consultadas; o projeto diz "inspirado em", nunca "réplica" |

## Erros da IA que a revisão humana apanhou

| Situação | O que estava errado | Como foi apanhado |
| --- | --- | --- |
| Pacote `ttyd` no Dockerfile (DEF-009) | Assumiu que o pacote existia no Debian 12 | O build falhou; o log foi lido e corrigido |
| Query com alias no HAVING (DEF-010) | Funcionava em SQLite, falhava em PostgreSQL | Validação no mesmo motor da produção |
| Contagem de critérios de aceitação | Um rascunho dizia 21; eram 15 | Contagem com `grep` nos ficheiros `.feature` |
| Verificação SQL de preço (consulta 7) | A primeira versão não detetava o DEF-002 | Teste da consulta com dados do modo desafio |
| Versões do PostgreSQL (DEF-011) | Cliente 15 e servidor 16 incompatíveis para backups | Análise de compatibilidade antes de usar o script |

## Regras que sigo

1. **Nunca colocar dados confidenciais** (de clientes, da empresa, credenciais, código proprietário) em ferramentas de IA
   não aprovadas. Exemplo real: neste projeto recusei usar o Jira corporativo a que a ferramenta tinha acesso; os defeitos
   vão para um Jira pessoal de testes (item F1).
2. **Tudo o que a IA produz é um rascunho:** só entra no projeto depois de executado e revisto.
3. **Validar no ambiente real:** o que passa num ambiente simplificado pode falhar no real (DEF-010, DEF-011).
4. **Rastreabilidade:** decisões importantes ficam escritas (bug reports, relatórios), não só na conversa com a IA.
5. **O conhecimento do negócio é meu:** a IA acelera, mas as regras de mercado e os riscos são validados por quem os conhece.

## v0.5.0 · Arquitetura de integração

- A IA ajudou a desenhar os padrões de integração (outbox, idempotência, DLQ, reciclagem) e os cenários de falha.
- Limite assumido: no ambiente onde a IA trabalhou não era possível correr Kafka. O código foi validado localmente com
  um barramento equivalente (ficheiro/memória) e o conector Kafka real é validado no pipeline, no ambiente QA.
  Isto ficou escrito na matriz de risco (T-06) em vez de ser escondido.
