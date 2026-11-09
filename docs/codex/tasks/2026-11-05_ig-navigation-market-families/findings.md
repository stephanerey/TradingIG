# Findings

- The adapter and discovery service already expose IG navigation pages, but the existing breadth-
  first discovery flattens products and loses their parent path.
- A full traversal is unnecessary for the IG-style interaction and consumes avoidable REST quota.
- The public navigation path can prove ancestry, while the reference market EPIC must remain an
  explicit family setting.
- Authenticated DEMO evidence on 2026-11-05 returned HTTP 404 for both `/market-navigation` and
  `/marketnavigation`; the session was closed after each bounded attempt.
- The active DEMO profile exposes `/categories` with the current `{code, nonTradeable}` shape.
  `INDICES` returned 67 reference contracts and `COMMODITIES` 73. Their entries expose exact
  `underlyingName`, EPIC, lot size and scaling factor, but no public derivative-parent link.
- Five reference candidates were observed as TRADEABLE: `IX.D.NASDAQ.IFD.IP`,
  `IX.D.CAC.IMF.IP`, `IX.D.DAX.IFMM.IP`, `CS.D.CFEGOLD.CEF.IP` and `CC.D.CL.UEF.IP`. This is
  availability evidence, not a silent global default or a Barrière/Option mapping.
