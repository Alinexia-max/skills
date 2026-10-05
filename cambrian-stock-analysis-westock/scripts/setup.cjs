#!/usr/bin/env node
'use strict';

/**
 * westock CLI 安装脚本（cambrian-stock-analysis-westock 技能自带）
 *
 * westock 是本技能唯一的定量数据源。此脚本用于在缺失时补装。
 *
 * 用法：
 *   node scripts/setup.cjs                     # 默认装到 ~/.local/bin
 *   node scripts/setup.cjs --dry-run           # 只打印不下载
 *   node scripts/setup.cjs --bindir <目录>      # 指定安装目录
 *   node scripts/setup.cjs --version v0.0.6    # 指定版本
 *   node scripts/setup.cjs --channel skillhub  # 换发布渠道（默认 workbuddy）
 *   node scripts/setup.cjs --help
 *
 * 实现说明：
 *   - 用 Node 内置 fetch 下载（本机 PowerShell 的 HTTPS 已损坏，不能用 Invoke-WebRequest/curl）
 *   - 下载后按同源 SHA256.txt 校验二进制完整性，校验失败拒绝安装
 *   - 不修改系统 PATH 之外的任何配置；会提示如何将安装目录加入 PATH
 *
 * 退出码：0 成功 / 1 失败
 */

const os = require('node:os');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const HOST = 'https://stockbuddy.qq.com/release';

function parseArgs(argv) {
  const opts = {
    channel: 'workbuddy',
    bindir: process.env.WESTOCK_INSTALL_DIR || path.join(os.homedir(), '.local', 'bin'),
    version: '',
    dryRun: false,
    yes: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--channel') opts.channel = argv[++i];
    else if (a === '--bindir' || a === '-d') opts.bindir = argv[++i];
    else if (a === '--version' || a === '-v') opts.version = argv[++i];
    else if (a === '--dry-run' || a === '-n') opts.dryRun = true;
    else if (a === '--yes' || a === '-y') opts.yes = true;
    else if (a === '--help' || a === '-h') opts.help = true;
    else {
      console.error(`未知参数: ${a}`);
      process.exit(1);
    }
  }
  return opts;
}

function detectArtifact() {
  const platform = os.platform();
  const arch = os.arch();
  const goos = platform === 'win32' ? 'windows' : platform === 'darwin' ? 'darwin' : platform === 'linux' ? 'linux' : null;
  if (!goos) {
    console.error(`不支持的操作系统: ${platform}`);
    process.exit(1);
  }
  const goarch = arch === 'x64' ? 'amd64' : arch === 'arm64' ? 'arm64' : null;
  if (!goarch) {
    console.error(`不支持的架构: ${arch}`);
    process.exit(1);
  }
  const ext = goos === 'windows' ? '.exe' : '';
  return { artifact: `westock-${goos}-${goarch}${ext}`, ext };
}

const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex').toLowerCase();

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(`westock CLI 安装脚本（需 Node >= 18）

用法:
  node scripts/setup.cjs                        # 装到 ~/.local/bin
  node scripts/setup.cjs --dry-run              # 只打印，不下载
  node scripts/setup.cjs --bindir "D:\\tools"    # 指定目录
  node scripts/setup.cjs --version v0.0.6       # 指定版本
  node scripts/setup.cjs --channel workbuddy    # 发布渠道（默认 workbuddy）

渠道说明:
  workbuddy  最新 v0.0.6（本机在用）
  skillhub   版本较旧（v0.0.2）`);
    process.exit(0);
  }

  const { artifact, ext } = detectArtifact();
  const base = `${HOST}/${opts.channel}/cli`;

  let version = opts.version;
  if (!version) {
    try {
      const res = await fetch(`${base}/latest.txt`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      version = (await res.text()).trim().split(/\r?\n/)[0];
    } catch (e) {
      console.error(`无法获取版本号 (${base}/latest.txt): ${e.message}`);
      process.exit(1);
    }
  }
  if (!version.startsWith('v')) version = `v${version}`;

  const url = `${base}/${version}/${artifact}`;
  const dest = path.join(opts.bindir, `westock${ext}`);

  console.log(`渠道:   ${opts.channel}`);
  console.log(`版本:   ${version}`);
  console.log(`下载:   ${url}`);
  console.log(`目标:   ${dest}`);

  if (opts.dryRun) {
    console.log('(dry-run) 未做任何改动');
    process.exit(0);
  }

  // 下载二进制
  let buf;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    buf = Buffer.from(await res.arrayBuffer());
    console.log(`已下载: ${buf.length} bytes`);
  } catch (e) {
    console.error(`下载失败: ${e.message}`);
    process.exit(1);
  }

  // 按同源 SHA256.txt 校验
  try {
    const res = await fetch(`${base}/${version}/SHA256.txt`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    const expected = text
      .split(/\r?\n/)
      .map((l) => l.trim())
      .find((l) => l.endsWith(artifact))
      ?.split(/\s+/)[0]
      ?.toLowerCase();
    if (!expected) {
      console.warn(`[!] SHA256.txt 中未找到 ${artifact}，跳过校验`);
    } else {
      const actual = sha256(buf);
      if (actual !== expected) {
        console.error('SHA256 校验失败，拒绝安装');
        console.error(`  期望: ${expected}`);
        console.error(`  实际: ${actual}`);
        process.exit(1);
      }
      console.log(`SHA256 校验通过: ${actual}`);
    }
  } catch (e) {
    console.warn(`[!] 无法获取 SHA256.txt，跳过校验: ${e.message}`);
  }

  // 已存在则先备份
  if (fs.existsSync(dest)) {
    const old = fs.readFileSync(dest);
    const oldHash = sha256(old);
    if (oldHash === sha256(buf)) {
      console.log('已是最新版本，无需安装。');
      process.exit(0);
    }
    const backup = `${dest}.bak`;
    try {
      fs.copyFileSync(dest, backup);
      console.log(`已备份旧版本 -> ${backup}`);
    } catch (e) {
      console.warn(`[!] 备份失败（继续）: ${e.message}`);
    }
  }

  // 写入
  try {
    fs.mkdirSync(opts.bindir, { recursive: true });
    fs.writeFileSync(dest, buf);
    if (ext === '') fs.chmodSync(dest, 0o755);
  } catch (e) {
    console.error(`写入失败: ${e.message}`);
    console.error(`  提示：若为权限问题，请改用 --bindir 指定一个可写目录。`);
    process.exit(1);
  }

  console.log(`[OK] 已安装 -> ${dest}`);

  // PATH 提示
  const pathEnv = process.env.PATH || '';
  const inPath = pathEnv.split(path.delimiter).includes(opts.bindir);
  if (inPath) {
    console.log(`PATH 已包含 ${opts.bindir}`);
  } else if (os.platform() === 'win32') {
    console.log(`\n请将以下目录加入用户 PATH（之后需重启终端/应用才生效）：`);
    console.log(`  ${opts.bindir}`);
    console.log(`或加入后直接以绝对路径调用：${dest}`);
  } else {
    console.log(`\n请将 ${opts.bindir} 加入 PATH：`);
    console.log(`  export PATH="${opts.bindir}:$PATH"`);
  }
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
