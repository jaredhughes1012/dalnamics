/** Full-page navigation, behind an object so tests can observe it. */
export const navigation = {
  assign: (url: string) => window.location.assign(url),
}
