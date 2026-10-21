// Run two independent JavaScript cookie implementations over cases read from stdin.
//
// Input (JSON): {"parse": [line, ...], "store": [[line, url, [retrieval url, ...]], ...]}.
// Output (JSON): {"versions": {...}, "parse": [...], "store": [...]}.
// "parse" uses the Set-Cookie parser of undici (Node.js fetch), "store" the cookie jar of
// tough-cookie. Both are installed into tests/upstream/oracle, see tests/test_oracles.py:
//   npm install --prefix tests/upstream/oracle --save-exact undici@8.12.3 tough-cookie@6.0.2
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.argv[2], "node_modules");
const { parseSetCookie } = require(path.join(root, "undici/lib/web/cookies/parse.js"));
const tough = require(path.join(root, "tough-cookie"));
const version = (name) =>
  JSON.parse(fs.readFileSync(path.join(root, name, "package.json"), "utf8")).version;

function parsed(line) {
  const found = parseSetCookie(line);
  if (found === null) return null;
  return {
    name: found.name,
    value: found.value,
    expires: found.expires ? found.expires.getTime() / 1000 : null,
    maxAge: found.maxAge === undefined ? null : found.maxAge,
    domain: found.domain === undefined ? null : found.domain,
    path: found.path === undefined ? null : found.path,
    secure: Boolean(found.secure),
    httpOnly: Boolean(found.httpOnly),
    sameSite: found.sameSite === undefined ? null : found.sameSite,
    unparsed: found.unparsed || [],
  };
}

function stored([line, url, retrievals]) {
  const jar = new tough.CookieJar(null, { looseMode: true, prefixSecurity: "silent" });
  let cookie;
  try {
    cookie = jar.setCookieSync(line, url);
  } catch (error) {
    return { stored: null, error: error.message };
  }
  if (!cookie) return { stored: null, error: "silently ignored" };
  return {
    stored: {
      name: cookie.key,
      value: cookie.value,
      domain: cookie.domain,
      hostOnly: cookie.hostOnly,
      path: cookie.path,
      secure: cookie.secure,
      httpOnly: cookie.httpOnly,
    },
    sent: retrievals.map((target) => jar.getCookiesSync(target).length === 1),
  };
}

const cases = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(
  JSON.stringify({
    versions: { undici: version("undici"), "tough-cookie": version("tough-cookie") },
    parse: (cases.parse || []).map(parsed),
    store: (cases.store || []).map(stored),
  }),
);
