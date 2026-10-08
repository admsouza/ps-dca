# Tasks — Estorno extra no SICONFI; auditoria do exercício anterior desligada

**Repo:** `ps-dca` · **Implementado antes da aprovação do PO, por decisão do dev (2026-10-06).
Pendências em `proposal.md`.**

## 0. Fundação
- [ ] 0.1 PO aprova a proposal (estorno no SICONFI, auditoria do anterior, percurso completo)

## 1. TEST
- [x] 1.1 `tests/pipeline/test_fonte_por_pedido.py`: SICONFI guarda o token; sem token apura; 403 mantido; fonte expõe o estorno só com token
- [x] 1.2 `tests/bf/test_estorno_receita_extra.py`: o anterior sem dados não abate
- [x] 1.3 `tests/msc/*`: o 409 vira sem dados, o 401 propaga, sem `/auditorias`, query no DTO

## 2. IMPLEMENT
- [x] 2.1 `app/routes/dependencias.py`: `_token_opcional` no caminho SICONFI
- [x] 2.2 `app/services/pipeline/apuracao.py`: SICONFI com token delega `estorno_*` à PublicSoft
- [x] 2.3 `app/services/bf/quadro_principal.py`: sem leitura no exercício, não abate
- [x] 2.4 `app/infra/msc/publicsoft.py`: sem pré-check, 409 vira sem dados, sem `tipoMatriz`

## 3. VERIFY
- [ ] 3.1 Produção: Cuitegi/2025 com `use_siconfi=true` → `L27` = 4486188.21, `L60` = 4479755.61
- [x] 3.2 Remover `PUBLICSOFT_AUDIT_URL` do `.env.example` (sem uso)

## 4. Arquivamento
- [ ] 4.1 Mesclar deltas em `openspec/specs/` após a aprovação do PO
