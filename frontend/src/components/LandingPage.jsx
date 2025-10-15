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
  Video,
  Sparkles,
  Zap,
  Shield,
  Cpu,
  Download,
} from "lucide-react";

const LandingPage = () => {
  const navigate = useNavigate();
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // 核心特性
  const features = [
    {
      icon: <Video className="w-8 h-8" />,
      title: "智能视频解析",
      description: "支持多种格式视频上传，自动提取音频和画面关键帧",
      color: "from-cyan-400 to-blue-500",
    },
    {
      icon: <Cpu className="w-8 h-8" />,
      title: "AI 深度分析",
      description: "利用先进的 AI 技术，自动识别语音、提取关键信息和生成摘要",
      color: "from-blue-400 to-indigo-500",
    },
    {
      icon: <FileText className="w-8 h-8" />,
      title: "结构化输出",
      description: "自动生成格式规范的 Markdown 文档，包含时间轴和内容大纲",
      color: "from-indigo-400 to-purple-500",
    },
  ];

  // 技术优势
  const advantages = [
    {
      icon: <Shield className="w-6 h-6" />,
      title: "数据安全",
      description: "本地部署，数据完全掌控",
    },
    {
      icon: <Zap className="w-6 h-6" />,
      title: "高效处理",
      description: "智能算法，快速生成报告",
    },
    {
      icon: <Sparkles className="w-6 h-6" />,
      title: "AI 驱动",
      description: "先进模型，精准识别内容",
    },
    {
      icon: <Download className="w-6 h-6" />,
      title: "开源免费",
      description: "MIT 协议，完全免费使用",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrollY > 50 ? "bg-white/95 backdrop-blur-lg shadow-lg" : "bg-white/80 backdrop-blur-md"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 py-5 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-primary-500 to-purple-600">
              <Video className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-brand-horizontal">
                VideoDevour
              </h1>
              <p className="text-xs text-gray-500">AI 视频智能分析</p>
            </div>
          </div>
          <div className="flex items-center space-x-6">
            <button
              onClick={() => navigate("/editor-test")}
              className="text-sm text-gray-600 hover:text-cyan-500 transition-colors font-medium hidden md:block"
            >
              📝 编辑器
            </button>
            <a
              href="https://github.com/datawhalechina/video-devour"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2 text-gray-600 hover:text-cyan-500 transition-colors"
            >
              <Github className="w-5 h-5" />
              <span className="hidden md:inline">GitHub</span>
            </a>
              <button
                onClick={() => navigate("/upload")}
                className="px-6 py-2.5 text-white rounded-lg transition-all text-sm font-medium shadow-lg hover:shadow-xl hover:scale-105 bg-gradient-brand"
              >
                开始使用
              </button>
          </div>
        </div>
      </nav>

      {/* 英雄区 */}
      <section className="pt-32 pb-24 px-6 relative overflow-hidden">
          {/* 装饰性背景 */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute top-20 left-10 w-72 h-72 rounded-full opacity-20 blur-3xl bg-gradient-brand"></div>
            <div className="absolute bottom-20 right-10 w-96 h-96 rounded-full opacity-20 blur-3xl bg-gradient-brand-reverse"></div>
          </div>

        <div className="max-w-5xl mx-auto text-center relative z-10">
          {/* 徽章 */}
          <div className="inline-flex items-center space-x-2 px-5 py-2.5 bg-white/80 backdrop-blur-sm rounded-full mb-8 shadow-lg border border-cyan-100">
            <Sparkles className="w-4 h-4 text-cyan-500" />
            <span className="text-sm font-medium bg-clip-text text-transparent bg-gradient-brand-horizontal">开源 · 免费 · AI 驱动</span>
          </div>

          {/* 主标题 */}
          <h1 className="text-6xl md:text-7xl font-bold mb-8 leading-relaxed tracking-tight">
            <span className="bg-clip-text text-transparent bg-gradient-brand">
              AI 视频内容
            </span>
            <br />
            <span className="text-gray-900">智能分析平台</span>
          </h1>

          {/* 副标题 */}
          <p className="text-xl md:text-2xl text-gray-600 mb-14 max-w-3xl mx-auto leading-loose">
            上传视频，让 AI 为您自动生成结构化笔记和内容摘要
            <br />
            <span className="text-cyan-600 font-medium">让知识提取变得简单高效</span>
          </p>

          {/* CTA 按钮组 */}
          <div className="flex flex-col sm:flex-row gap-5 justify-center items-center mb-12">
            <button
              onClick={() => navigate("/upload")}
              className="group flex items-center space-x-2 px-10 py-4 text-white rounded-xl transition-all font-semibold shadow-2xl hover:shadow-cyan-500/50 hover:scale-105 bg-gradient-brand"
            >
              <Upload className="w-5 h-5" />
              <span>立即开始</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="https://github.com/datawhalechina/video-devour"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2 px-10 py-4 bg-white border-2 border-cyan-300 text-gray-900 rounded-xl hover:border-cyan-400 hover:shadow-xl transition-all font-semibold"
            >
              <Github className="w-5 h-5" />
              <span>查看源码</span>
            </a>
          </div>

          {/* 特性标签 */}
          <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-600">
            <div className="flex items-center space-x-2 px-4 py-2 bg-white/60 backdrop-blur-sm rounded-lg">
              <Shield className="w-4 h-4 text-cyan-500" />
              <span>数据安全</span>
            </div>
            <div className="flex items-center space-x-2 px-4 py-2 bg-white/60 backdrop-blur-sm rounded-lg">
              <Zap className="w-4 h-4 text-cyan-500" />
              <span>快速处理</span>
            </div>
            <div className="flex items-center space-x-2 px-4 py-2 bg-white/60 backdrop-blur-sm rounded-lg">
              <Code className="w-4 h-4 text-cyan-500" />
              <span>MIT 开源</span>
            </div>
          </div>
        </div>
      </section>

      {/* 核心功能 */}
      <section className="py-28 px-6 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
              <span className="bg-clip-text text-transparent bg-gradient-brand-horizontal">
                核心功能
              </span>
            </h2>
            <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
              从视频上传到报告生成，全程自动化智能处理
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group relative bg-gradient-to-br from-white to-gray-50 p-8 rounded-2xl border-2 border-gray-100 hover:border-cyan-200 hover:shadow-2xl transition-all duration-300 overflow-hidden"
              >
                {/* 装饰性渐变背景 */}
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-5 transition-opacity duration-300`}></div>
                
                  <div className="relative z-10">
                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 text-white shadow-lg group-hover:scale-110 transition-transform duration-300 bg-gradient-brand">
                      {feature.icon}
                    </div>
                  <h3 className="text-xl font-bold mb-4 text-gray-900 leading-snug">{feature.title}</h3>
                  <p className="text-gray-600 leading-loose text-base">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 技术优势 */}
      <section className="py-28 px-6 bg-gradient-to-br from-gray-50 to-cyan-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-gray-900 tracking-tight">为什么选择我们</h2>
            <p className="text-lg md:text-xl text-gray-600 leading-relaxed">专业、安全、高效的视频分析解决方案</p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {advantages.map((advantage, index) => (
              <div
                key={index}
                className="bg-white/80 backdrop-blur-sm p-6 rounded-xl shadow-lg hover:shadow-2xl transition-all hover:scale-105 border border-cyan-100"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5 text-white bg-gradient-brand">
                  {advantage.icon}
                </div>
                <h3 className="text-lg font-bold mb-3 text-gray-900 leading-snug">{advantage.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{advantage.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 技术栈说明 */}
      <section className="py-28 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
              <span className="bg-clip-text text-transparent bg-gradient-brand-horizontal">
                技术栈
              </span>
            </h2>
            <p className="text-lg md:text-xl text-gray-600 leading-relaxed">基于现代化技术构建</p>
          </div>
          
          <div className="relative">
            {/* 装饰背景 */}
            <div className="absolute inset-0 rounded-2xl opacity-5 bg-gradient-brand"></div>
            
            <div className="relative bg-gray-900 text-white p-10 rounded-2xl shadow-2xl border-2 border-gray-800">
              <pre className="text-sm md:text-base overflow-x-auto leading-loose">
                <code className="language-json">{`{
  "frontend": {
    "framework": "React 18",
    "styling": "Tailwind CSS",
    "editor": "Slate.js",
    "build": "Vite"
  },
  "backend": {
    "runtime": "Python",
    "framework": "FastAPI",
    "ai": "OpenAI API (可自定义)"
  },
  "features": {
    "asr": "语音识别引擎",
    "vlm": "视觉语言模型",
    "output": "Markdown 格式"
  },
  "deployment": {
    "type": "自托管",
    "docker": "支持"
  }
}`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* 快速开始 */}
      <section className="py-28 px-6 bg-gradient-to-br from-cyan-50 to-blue-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-gray-900 tracking-tight">快速开始</h2>
            <p className="text-lg md:text-xl text-gray-600 leading-relaxed">几行命令即可启动项目</p>
          </div>
          
          <div className="bg-white rounded-2xl shadow-2xl p-8 md:p-10 border-2 border-cyan-100">
            <div className="space-y-8">
              <div className="flex items-start space-x-4 group">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0 bg-gradient-brand">
                  1
                </div>
                <div className="flex-1 bg-gray-900 rounded-xl p-5 group-hover:shadow-xl transition-shadow">
                  <p className="text-cyan-400 text-sm mb-3 font-medium">克隆仓库</p>
                  <code className="text-green-400 text-sm md:text-base leading-relaxed">
                    git clone https://github.com/datawhalechina/video-devour.git
                  </code>
                </div>
              </div>
              
              <div className="flex items-start space-x-4 group">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0 bg-gradient-brand">
                  2
                </div>
                <div className="flex-1 bg-gray-900 rounded-xl p-5 group-hover:shadow-xl transition-shadow">
                  <p className="text-cyan-400 text-sm mb-3 font-medium">安装依赖</p>
                  <code className="text-green-400 text-sm md:text-base leading-relaxed">
                    cd video-devour && pip install -r requirements.txt && cd frontend && npm install
                  </code>
                </div>
              </div>
              
              <div className="flex items-start space-x-4 group">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0 bg-gradient-brand">
                  3
                </div>
                <div className="flex-1 bg-gray-900 rounded-xl p-5 group-hover:shadow-xl transition-shadow">
                  <p className="text-cyan-400 text-sm mb-3 font-medium">启动服务</p>
                  <code className="text-green-400 text-sm md:text-base leading-relaxed">
                    # 后端: python -m uvicorn backend.api.main:app --reload
                    <br />
                    # 前端: cd frontend && npm run dev
                  </code>
                </div>
              </div>
            </div>
            
            <div className="mt-8 pt-8 border-t border-gray-200 text-center">
              <a
                href="https://github.com/datawhalechina/video-devour#readme"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-cyan-600 hover:text-cyan-700 transition-colors font-medium"
              >
                <FileText className="w-5 h-5" />
                <span>查看完整文档</span>
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* 开源贡献 */}
      <section className="py-28 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
              <span className="bg-clip-text text-transparent bg-gradient-brand-horizontal">
                加入我们
              </span>
            </h2>
            <p className="text-lg md:text-xl text-gray-600 mb-5 leading-relaxed">
              这是一个开源项目，欢迎任何形式的贡献
            </p>
            <p className="text-base text-gray-500 leading-relaxed">
              代码、文档、建议或 Bug 报告都很有价值
            </p>
          </div>
          
          <div className="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-2xl p-10 border-2 border-cyan-100">
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="bg-white p-7 rounded-xl shadow-lg hover:shadow-2xl transition-all">
                <Github className="w-10 h-10 text-cyan-500 mb-5" />
                <h3 className="text-xl font-bold mb-3 text-gray-900 leading-snug">提交 Issue</h3>
                <p className="text-gray-600 mb-5 text-sm leading-relaxed">发现 Bug 或有新想法？欢迎提交 Issue 与我们交流</p>
                <a
                  href="https://github.com/datawhalechina/video-devour/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-2 text-cyan-600 hover:text-cyan-700 font-medium transition-colors"
                >
                  <span>去提交</span>
                  <ArrowRight className="w-4 h-4" />
                </a>
              </div>
              
              <div className="bg-white p-7 rounded-xl shadow-lg hover:shadow-2xl transition-all">
                <Code className="w-10 h-10 text-cyan-500 mb-5" />
                <h3 className="text-xl font-bold mb-3 text-gray-900 leading-snug">贡献代码</h3>
                <p className="text-gray-600 mb-5 text-sm leading-relaxed">Fork 项目，提交 PR，让这个项目变得更好</p>
                <a
                  href="https://github.com/datawhalechina/video-devour/pulls"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-2 text-cyan-600 hover:text-cyan-700 font-medium transition-colors"
                >
                  <span>去贡献</span>
                  <ArrowRight className="w-4 h-4" />
                </a>
              </div>
            </div>
            
            <div className="text-center">
              <a
                href="https://github.com/datawhalechina/video-devour"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 px-8 py-4 text-white rounded-xl transition-all font-semibold shadow-lg hover:shadow-2xl hover:scale-105 bg-gradient-brand"
              >
                <Github className="w-5 h-5" />
                <span>访问 GitHub 仓库</span>
                <ArrowRight className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="bg-gradient-to-br from-gray-900 to-gray-800 text-white py-16 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-12 mb-12">
            {/* 品牌信息 */}
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-brand">
                  <Video className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold">VideoDevour</span>
              </div>
              <p className="text-gray-400 text-sm leading-loose">
                AI 驱动的视频内容智能分析平台，让知识提取变得简单高效
              </p>
            </div>
            
            {/* 快速链接 */}
            <div>
              <h3 className="text-lg font-bold mb-5">快速链接</h3>
              <ul className="space-y-4 text-sm">
                <li>
                  <a
                    href="https://github.com/datawhalechina/video-devour"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-cyan-400 transition-colors flex items-center space-x-2"
                  >
                    <Github className="w-4 h-4" />
                    <span>GitHub 仓库</span>
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/datawhalechina/video-devour#readme"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-cyan-400 transition-colors flex items-center space-x-2"
                  >
                    <FileText className="w-4 h-4" />
                    <span>使用文档</span>
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/datawhalechina/video-devour/issues"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-cyan-400 transition-colors flex items-center space-x-2"
                  >
                    <Code className="w-4 h-4" />
                    <span>问题反馈</span>
                  </a>
                </li>
              </ul>
            </div>
            
            {/* 开源信息 */}
            <div>
              <h3 className="text-lg font-bold mb-5">开源协议</h3>
              <div className="text-gray-400 text-sm space-y-4 leading-relaxed">
                <p>MIT License © 2024</p>
                <p>完全开源免费使用</p>
                <div className="flex items-center space-x-2 pt-2">
                  <Heart className="w-4 h-4 text-red-500 fill-red-500" />
                  <span className="text-xs">Made by Open Source Community</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="pt-8 border-t border-gray-700">
            <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0 text-sm text-gray-400">
              <div>
                <p>Datawhale · VideoDevour Project</p>
              </div>
              <div className="flex items-center space-x-6">
                <a 
                  href="https://github.com/datawhalechina/video-devour/blob/main/LICENSE" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-400 transition-colors"
                >
                  许可证
                </a>
                <a 
                  href="https://github.com/datawhalechina" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-400 transition-colors"
                >
                  关于 Datawhale
                </a>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
