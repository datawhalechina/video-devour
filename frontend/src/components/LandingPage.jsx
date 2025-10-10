import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  BarChart3,
  FileText,
  ArrowRight,
  Github,
  Code,
  Heart,
  Terminal,
} from "lucide-react";

const LandingPage = () => {
  const navigate = useNavigate();
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // 核心特性 - 简化版
  const features = [
    {
      icon: <Upload className="w-6 h-6" />,
      title: "上传视频",
      description: "拖拽上传，支持常见格式",
    },
    {
      icon: <BarChart3 className="w-6 h-6" />,
      title: "AI 分析",
      description: "自动提取关键信息",
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: "Markdown 报告",
      description: "获取结构化分析结果",
    },
  ];

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* 极简导航栏 */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrollY > 50 ? "bg-white/90 backdrop-blur-md shadow-sm" : "bg-transparent"
        }`}
      >
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Terminal className="w-6 h-6 text-gray-900" />
            <h1 className="text-xl font-bold">VideoDevour</h1>
          </div>
          <div className="flex items-center space-x-6">
            <button
              onClick={() => navigate("/editor-test")}
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors font-medium"
            >
              📝 编辑器测试
            </button>
            <a
              href="https://github.com/datawhalechina/video-devour"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <Github className="w-5 h-5" />
              <span className="hidden md:inline">GitHub</span>
            </a>
            <button
              onClick={() => navigate("/upload")}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
            >
              开始使用
            </button>
          </div>
        </div>
      </nav>

      {/* 极简英雄区 */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          {/* 开源标签 */}
          <div className="inline-flex items-center space-x-2 px-4 py-2 bg-gray-100 rounded-full mb-8">
            <Code className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-600">开源 · 免费 · 自托管</span>
          </div>

          {/* 主标题 */}
          <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
            AI 视频分析工具
          </h1>

          {/* 副标题 */}
          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed">
            一个简单的开源项目，帮助你快速分析视频内容。
            <br />
            上传视频，获取 AI 生成的分析报告。
          </p>

          {/* CTA 按钮组 */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button
              onClick={() => navigate("/upload")}
              className="group flex items-center space-x-2 px-8 py-4 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-all font-medium"
            >
              <span>开始使用</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="https://github.com/datawhalechina/video-devour"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2 px-8 py-4 border-2 border-gray-900 text-gray-900 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              <Github className="w-5 h-5" />
              <span>查看源码</span>
            </a>
          </div>

          {/* 简单说明 */}
          <p className="mt-8 text-sm text-gray-500">
            MIT License · 无需注册 · 数据本地处理
          </p>
        </div>
      </section>

      {/* 核心功能 - 极简卡片 */}
      <section className="py-20 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-16">
            三步完成分析
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white p-8 rounded-lg border border-gray-200 hover:border-gray-400 transition-all"
              >
                <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center mb-4 text-gray-900">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-600 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 技术栈说明 */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">技术栈</h2>
          <div className="bg-gray-900 text-white p-8 rounded-lg">
            <pre className="text-sm overflow-x-auto">
              <code>{`{
  "frontend": {
    "framework": "React 18",
    "styling": "Tailwind CSS",
    "build": "Vite"
  },
  "backend": {
    "runtime": "Node.js",
    "ai": "OpenAI API (可自定义)"
  },
  "deployment": {
    "type": "自托管",
    "docker": "支持"
  }
}`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* 快速开始 */}
      <section className="py-20 px-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">快速开始</h2>
          <div className="bg-gray-900 text-white p-8 rounded-lg space-y-4">
            <div className="flex items-start space-x-4">
              <span className="text-gray-500">#</span>
              <div className="flex-1">
                <p className="text-gray-400 text-sm mb-1">克隆仓库</p>
                <code className="text-green-400">
                  git clone https://github.com/yourusername/video-react.git
                </code>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <span className="text-gray-500">#</span>
              <div className="flex-1">
                <p className="text-gray-400 text-sm mb-1">安装依赖</p>
                <code className="text-green-400">npm install</code>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <span className="text-gray-500">#</span>
              <div className="flex-1">
                <p className="text-gray-400 text-sm mb-1">启动开发服务器</p>
                <code className="text-green-400">npm run dev</code>
              </div>
            </div>
          </div>
          <div className="mt-8 text-center">
            <a
              href="https://github.com"
              className="inline-flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <span>查看完整文档</span>
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* 开源贡献 */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">参与贡献</h2>
          <p className="text-gray-600 mb-8 text-lg">
            这是一个开源项目，欢迎任何形式的贡献。
            <br />
            代码、文档、建议或 Bug 报告都很有价值。
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              <Github className="w-5 h-5" />
              <span>提交 Issue</span>
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-6 py-3 border-2 border-gray-900 text-gray-900 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Code className="w-5 h-5" />
              <span>贡献代码</span>
            </a>
          </div>
        </div>
      </section>

      {/* 极简页脚 */}
      <footer className="border-t border-gray-200 py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="flex items-center space-x-2 text-gray-600">
              <Terminal className="w-5 h-5" />
              <span className="font-semibold">VideoDevour</span>
            </div>
            
            <div className="flex items-center space-x-6 text-sm text-gray-600">
              <a
                href="https://github.com/datawhalechina/video-devour"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-gray-900 transition-colors"
              >
                GitHub
              </a>
              <a 
                href="https://github.com/datawhalechina/video-devour#readme" 
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-gray-900 transition-colors"
              >
                文档
              </a>
              <a 
                href="https://github.com/datawhalechina/video-devour/blob/main/LICENSE" 
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-gray-900 transition-colors"
              >
                许可证
              </a>
            </div>

            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <span>Made with</span>
              <Heart className="w-4 h-4 text-red-500 fill-red-500" />
              <span>by Open Source Community</span>
            </div>
          </div>

          <div className="mt-8 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
            <p>MIT License © 2024 · 完全开源免费</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
