// Roll up the daily "Today" achieved figures into a month total.
// `days` is the bd.days map keyed by YYYY-MM-DD; `ym` is "YYYY-MM".
export function monthAchieved(days, ym) {
  let sales = 0
  let collection = 0
  for (const [date, day] of Object.entries(days || {})) {
    if (date.slice(0, 7) !== ym) continue
    sales += Number(day?.today?.salesAchieved) || 0
    collection += Number(day?.today?.collAchieved) || 0
  }
  return { sales, collection }
}
