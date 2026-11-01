# AF Crédito Vale do Ribeira — Instagram automatizado

Criador de artes JPG por templates e publicação na Graph API com **Facebook Login**. Repositório público, sem tokens no código. A publicação começa **desativada**.

## O que faz
- 4 publicações por dia, horário America/Sao_Paulo: **09h14, 12h14, 15h14, 19h14**.
- 3 Stories (09/15/19) e 1 arte de feed (12).
- Temas por dia da semana: CLT, conta de luz, INSS, servidor, FGTS, educação financeira e atendimento.
- Imagens criadas com Pillow, gratuitamente, e disponibilizadas por GitHub Pages.
- Bloqueio de identidade: somente Instagram **@afcredito.valedoribeira** e conta BUSINESS.
- Textos são pré-definidos e se repetem semanalmente. **Não é IA generativa de artes inéditas**.

## Configuração inicial (na ordem)
1. Em **Settings > Pages**: deploy from a branch **main /docs**. O Pages deve ter endereço `https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto/`.
2. Em **Settings > Secrets and variables > Actions > Secrets**, adicione **META_ACCESS_TOKEN** com seu token, sem colá-lo em Issues, arquivos ou mensagens. Se a descoberta do Instagram falhar, configure também **IG_USER_ID** (ID numérico da conta Instagram, não @usuario).
3. Em **Settings > Secrets and variables > Actions > Variables**, mantenha **PUBLISH_ENABLED=false** (criada na instalação).
4. Em **Actions > Preparar calendário e artes > Run workflow**, escolha `start=2026-11-02` e `days=14`. O fluxo cria arquivos em `docs/media` e `docs/calendario.csv`. Confira a arte `https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto/media/2026-11-02_12.jpg`.
5. Em **Actions > Instagram AF Crédito — conferir ou publicar > Run workflow**, escolha `mode=validate`. Ele **não publica**: confirma usuário, tipo Business e tenta verificar permissões e quota. Se o token for de Página, a leitura das permissões pode não estar disponível, sem invalidar a identidade.
6. Confira as imagens e textos em `docs/media` e `docs/calendario.csv`. Faça `mode=dry-run` para testar o conteúdo da data sem chamar a Meta.
7. Somente após aprovar tudo, altere a variável **PUBLISH_ENABLED=true**. O primeiro `mode=publish` enviará uma publicação real; confira-a no Instagram.

## Permissões Facebook Login
A autorização precisa cobrir `pages_show_list`, `pages_read_engagement`, `instagram_basic` e `instagram_content_publish`. Para Stories, a conta Instagram deve ser Business e conectada à Página Facebook. Token de WhatsApp ou anúncios sem essas permissões não serve. O acesso precisa continuar válido.

## Atenções
- GitHub Actions agenda em UTC; as horas acima usam São Paulo (UTC-3), atualmente sem horário de verão.
- O agendador do GitHub **não garante minuto exato** e pode atrasar ou não executar uma ocorrência.
- O Graph API permite enviar imagens públicas ao feed e Stories, mas Stories criados pela API não possuem figurinha de link; deixe CTA na própria imagem.
- `docs/published.json` ajuda a evitar duplicação. Se um workflow falhar **após publicar** e antes de registrar o ID, confira no Instagram antes de executar novamente.
- Para alterar ofertas/condições, edite `THEMES` em `bot.py`. Não crie promessas de aprovação, taxas ou limites não verificados.
- Publicar no GitHub Pages exige o Pages habilitado e o arquivo JPG acessível por HTTPS.
