require "formula"

class Finquant < Formula
  desc "智能量化交易平台 - 回测 / 模拟 / 实盘"
  homepage "https://meepoquant.com"
  url "https://github.com/meepo-quant/finquant.git", tag: "v#{version}", revision: "HEAD"
  license "MIT"
  version "#{version}"

  depends_on "python@3.11"

  def install
    # 安装完整依赖
    system "pip3", "install", "--no-deps", "."
    system "pip3", "install",
      "pandas>=1.3.0",
      "numpy>=1.20.0",
      "scipy>=1.8.0",
      "finshare>=1.0.2",
      "websockets>=10.0",
      "aiohttp>=3.8.0",
      "requests>=2.28.0",
      "prompt_toolkit>=3.0"

    bin.install_symlink "#{lib}/python3.11/site-packages/finquant/console/rich_console.py"
    (bin/"finquant").write <<~PYTHON
      #!/usr/bin/env python3
      import sys
      from finquant.console.rich_console import main
      sys.exit(main())
    PYTHON
    chmod "+x", bin/"finquant"
  end

  def caveats
    <<~EOS
      安装完成！

      使用方法:
        finquant              # 启动美化控制台
        finquant --help      # 查看帮助

      首次运行需要配置券商账户:
        finquant
        > broker add
    EOS
  end

  test do
    system "python3", "-c", "import finquant; print('finquant installed"
  end
 successfully')end
