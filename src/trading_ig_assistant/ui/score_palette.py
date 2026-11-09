"""Shared accessible palette for the approved ordinal scanner scale."""

from trading_ig_assistant.domain.analysis import ScoreBand

SCORE_BAND_COLORS = {
    ScoreBand.EXCEPTIONAL: ("#ffffff", "#075c36"),
    ScoreBand.FAVORABLE: ("#0f6b3e", "#dff3e7"),
    ScoreBand.CAUTION: ("#7a4d00", "#fff3cd"),
    ScoreBand.UNFAVORABLE: ("#a61b1b", "#fde7e7"),
    ScoreBand.UNKNOWN: ("#4f5965", "#eef1f4"),
}
