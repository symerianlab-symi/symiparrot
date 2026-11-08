// codex | 2026-10-13 | protocol_version: 1
import assert from "node:assert/strict";
import { rmSync } from "node:fs";
import { lstat, mkdtemp, readFile, realpath, writeFile } from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import { isAbsolute, join, resolve } from "node:path";
import { browserAccessArguments, readBrowserAccessPolicy } from "./browser-access/policy.mjs";
import { checkNodeVersion } from "./platform.mjs";

const ENTRY = "./runtime/apps/cli/lib/bin.js";
const RUNTIME = "runtime/apps/cli";
const HELP = `Symi — Jai Host, Web UI and CLI

  symi                         start the Web UI
  symi web [options]           start the Web UI with native options
  symi cli [options]           open the native CLI using this home's shared Host
  symi cli --connect <origin>  attach to a running Host without local startup
  symi cli login <origin> --name <name>  pair with a Host through browser approval
  symi cli --connection <name>  use a remembered Host connection
  symi web --enable-migration  enable reviewed native memory imports for this Host
  symi archive|migrate --help  explicit private legacy data utilities
  symi browser-access [...]   pin browser access to one Tailscale node
  symi host status|stop|owner-link  inspect, stop or sign in to this home's Host
  symi --profile <name> [...]  launch an explicit native profile
  symi plugin --profile <name> [...]  manage native profile plugins

SYMI_HOME selects the data home (default ~/.symi-jai). HOME is unchanged.
Web workspaces default to ~/SYMI-WS on the Host. Choose another in Features > Workspace.
Existing Symi data is not imported. CLI workspaces refer to the connected Host.
Use symi web --help for native Web options; that command prepares a profile.
`;

function homePath(value, osHome) {
  assert(typeof value === "string" && value.trim(), "The Symi home must not be empty.");
  const expanded =
    value === "~" ? osHome : value.startsWith("~/") ? join(osHome, value.slice(2)) : value;
  assert(isAbsolute(expanded), "The Symi home must be an absolute path.");
  return resolve(expanded);
}

/** Identify the native invocation prefix solely to place product overlays. */
function invocation(argv) {
  const args = argv.length ? [...argv] : ["web"];
  if (args[0] === "tui") {
    throw new Error("The old tui command is unavailable. Use symi cli for the native terminal.");
  }
  if (args[0] === "cli") {
    return {
      args: ["tui", ...args.slice(1)],
      profile: undefined,
      defaultOnly: false,
      insertion: 0,
    };
  }
  if (args[0] === "host" || args[0] === "plugin") {
    return { args, profile: undefined, defaultOnly: false, insertion: 0 };
  }
  const alias = args[0] === "web";
  let profile = alias ? "web" : undefined;
  let defaultOnly = false;
  for (let index = alias ? 1 : 0; index < args.length; index++) {
    const arg = args[index];
    if (!alias && arg === "--profile") {
      profile = args[++index];
    } else if (!alias && arg.startsWith("--profile=")) {
      profile = arg.slice("--profile=".length);
    } else if (arg === "--patch") {
      index++;
    } else if (arg.startsWith("--patch=") || arg === "--adopt-home" || arg === "--dump-config") {
      continue;
    } else if (arg === "--dump-default-config") {
      defaultOnly = true;
    } else {
      break;
    }
  }
  assert(
    profile !== undefined,
    "This command is unavailable in the Jai-based Symi product. Use symi --help; no legacy command will run.",
  );
  return { args, profile, defaultOnly, insertion: alias ? 1 : 0 };
}

async function ownedFile(root, path) {
  const expected = join(root, path);
  const actual = await realpath(expected);
  assert.equal(
    actual,
    expected,
    `Symi distribution file must remain at its admitted path: ${path}`,
  );
  assert((await lstat(expected)).isFile(), `Symi distribution file must be regular: ${path}`);
  return actual;
}

/** Compose the product layer once for sealed and source-development launches. */
export async function composeProductOverlay({
  root,
  home,
  osHome,
  workspacePath = join(osHome, "SYMI-WS"),
  profile,
  enableMigration = false,
  append = [],
}) {
  const overlay = JSON.parse(await readFile(await ownedFile(root, "product.patch.json"), "utf8"));
  if (profile === "web") {
    overlay.push({ id: "workspace", config: { defaultPath: workspacePath } });
    overlay.push({ id: "directory-picker", disabled: true });
    overlay.push({ id: "client-ui-memory", config: { placement: "features" } });
    overlay.push({ id: "ui-desktop-control", config: { placement: "features" } });
    overlay.push({ id: "session-log-download", config: { placement: "features" } });
    overlay.push({ id: "ui-trajectory", disabled: true });
    overlay.push({
      insert: [
        {
          id: "symi-workspace-picker-host",
          name: "@jai-ai/jai-host-directory-picker-browse",
        },
        {
          id: "symi-workspace-picker",
          name: "@jai-ai/jai-client-ui-directory-picker-browse",
        },
        { id: "symi-presentation", name: await ownedFile(root, "presentation/index.mjs") },
        {
          id: "symi-connections",
          name: await ownedFile(root, "integrations/index.mjs"),
          config: { management: true, stateDir: join(home, "integrations") },
        },
      ],
    });
  }
  if (enableMigration) {
    overlay.push({
      insert: [
        {
          id: "symi-memory-migration",
          name: await ownedFile(root, "migration/host.mjs"),
          config: { home },
        },
      ],
    });
  }
  assert(Array.isArray(append), "Additional product overlay rows must be an array.");
  return [...overlay, ...append];
}

/** Prepare the admitted native entry and a process-owned overlay without touching user data. */
export async function prepareLaunch({
  directory,
  argv,
  environment = process.env,
  osHome = homedir(),
  platform = {
    os: process.platform,
    arch: process.arch,
    nodeMajor: Number(process.versions.node.split(".")[0]),
  },
}) {
  checkNodeVersion();
  const root = await realpath(directory);
  const carrier = JSON.parse(await readFile(await ownedFile(root, "carrier.json"), "utf8"));
  assert.equal(carrier.entry, ENTRY, "Symi carrier names an unsupported native entry.");
  assert.equal(
    carrier.runtimePackage,
    RUNTIME,
    "Symi carrier names an unsupported runtime package.",
  );
  assert.deepEqual(
    carrier.platform,
    platform,
    "This Symi artifact requires its admitted platform and Node major.",
  );
  const entry = await ownedFile(root, ENTRY);
  const product = JSON.parse(await readFile(await ownedFile(root, "package.json"), "utf8"));
  assert.equal(product.name, "@symerian/symi-parrot", "Symi product metadata is missing."); // symiparrot fork
  assert.equal(typeof product.version, "string", "Symi product version is missing.");
  assert.deepEqual(
    carrier.product,
    { name: product.name, version: product.version, bin: "symiparrot" }, // symiparrot fork
    "Symi carrier/product metadata differ.",
  );
  if (argv.length === 1 && ["--help", "-h", "--version", "-V"].includes(argv[0])) {
    return { output: argv[0] === "--help" || argv[0] === "-h" ? HELP : `${product.version}\n` };
  }
  if (argv.length === 2 && argv[0] === "cli" && ["--version", "-V"].includes(argv[1])) {
    return { output: `${product.version}\n` };
  }
  const outerEntry = ["archive", "migrate"].includes(argv[0])
    ? "migration/cli.mjs"
    : argv[0] === "browser-access"
      ? "browser-access/cli.mjs"
      : undefined;
  const enableMigration = argv[0] === "web" && argv[1] === "--enable-migration";
  const nativeArgs = enableMigration ? ["web", ...argv.slice(2)] : argv;
  const command = outerEntry ? { args: argv, profile: undefined } : invocation(nativeArgs);
  const selected = environment.SYMI_HOME ?? environment.JAI_HOME ?? join(osHome, ".symi-jai");
  const home = homePath(selected, osHome);
  if (environment.SYMI_HOME !== undefined && environment.JAI_HOME !== undefined) {
    assert.equal(
      homePath(environment.JAI_HOME, osHome),
      home,
      "SYMI_HOME and JAI_HOME select different homes.",
    );
  }
  const env = { ...environment, SYMI_HOME: home, JAI_HOME: home, JAI_TELEMETRY_DISABLED: "1" };
  // Source admission is owned only by the development supervisor. Never let
  // an ambient dev shell alter the sealed product's native module authority.
  delete env.SYMI_DEV_JAI_SOURCE_ROOT;
  if (outerEntry) {
    return {
      entry: await ownedFile(root, outerEntry),
      args: argv,
      environment: env,
      cleanup: () => {},
    };
  }
  if (command.args[0] !== "host") {
    env.JAI_DISTRIBUTION_DEFAULTS = await ownedFile(root, "defaults.json");
  }
  const args = command.args;
  const browserPolicy =
    !command.defaultOnly && command.profile === "web"
      ? await readBrowserAccessPolicy(home)
      : undefined;
  const browserArgs =
    browserPolicy === undefined ? [] : browserAccessArguments(args, browserPolicy);
  let temporary;
  const cleanup = () => {
    if (temporary !== undefined) {
      rmSync(temporary, { recursive: true, force: true });
      temporary = undefined;
    }
  };
  try {
    if (!command.defaultOnly && ["web", "headless"].includes(command.profile)) {
      const overlay = await composeProductOverlay({
        root,
        home,
        osHome,
        profile: command.profile,
        enableMigration,
      });
      temporary = await mkdtemp(join(tmpdir(), "symi-launch-"));
      const patch = join(temporary, "product.patch.json");
      await writeFile(patch, JSON.stringify(overlay), { mode: 0o600 });
      args.splice(command.insertion, 0, "--patch", patch);
    }
    args.push(...browserArgs);
    return { entry, args, environment: env, cleanup };
  } catch (error) {
    cleanup();
    throw error;
  }
}
