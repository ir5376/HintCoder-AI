function detectProvider(url) {
  let hostname = '';
  try {
    hostname = new URL(url).hostname.toLowerCase();
  } catch (error) {
    return null;
  }

  if (hostname === 'leetcode.com' || hostname.endsWith('.leetcode.com')) {
    return 'leetcode';
  }
  if (hostname === 'school.programmers.co.kr') {
    return 'programmers';
  }
  if (hostname === 'www.acmicpc.net' || hostname === 'acmicpc.net') {
    return 'boj';
  }
  if (hostname === 'codeforces.com' || hostname.endsWith('.codeforces.com')) {
    return 'codeforces';
  }
  if (hostname === 'atcoder.jp' || hostname.endsWith('.atcoder.jp')) {
    return 'atcoder';
  }

  return null;
}

if (typeof module !== 'undefined') {
  module.exports = { detectProvider };
}
