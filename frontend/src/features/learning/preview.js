// 本地预览独立于任务目录，不写入后端或触发模型调用。
export const isLearningPreview = (taskId) =>
  taskId === "preview-design" &&
  ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const report = {
  task_id: "preview-design",
  video_name: "空间里的设计智慧",
  duration: "18:24",
  final_report:
    "# 空间里的设计智慧\n\n## 留白\n\n为光线、活动和情绪保留余地。留白是有意的减法，让空间更透气，也给注意力留下呼吸的空间。\n\n## 自然光\n\n清晨柔和、午后明亮、黄昏温暖。不同的光线让空间拥有不同的情绪。\n\n## 材质\n\n天然材料的触感与时间留下的痕迹，让空间更接近真实生活。\n\n## 生活动线\n\n以真实的生活习惯规划动线，让活动自然流畅。",
};
const questions = [
  {
    id: "q1",
    type: "single",
    chapter: "留白",
    question: "在空间设计中，留白的主要作用是什么？",
    options: [
      "增加装饰元素",
      "为光线与活动保留空间",
      "减少所有家具",
      "统一所有材质",
    ],
    answer: [1],
    explanation: "通过减少视觉干扰，为自然光、人的活动与情绪提供空间。",
  },
  {
    id: "q2",
    type: "multiple",
    chapter: "自然光",
    question: "自然光可以带来哪些变化？",
    options: ["时间的感知", "空间情绪的变化", "消除所有阴影", "温暖的体验"],
    answer: [0, 1, 3],
    explanation: "自然光让人感受时间流逝，并改变空间的情绪与温度感。",
  },
  {
    id: "q3",
    type: "boolean",
    chapter: "生活动线",
    question: "生活动线应当符合真实的生活习惯。",
    options: ["正确", "错误"],
    answer: [0],
    explanation: "动线服务于人的日常活动，应自然流畅。",
  },
];
export function learningPreview(endpoint, body) {
  if (endpoint === "report") return report;
  if (endpoint === "mindmap")
    return {
      html: '<script type="text/template"># 空间里的设计智慧\n## 留白\n- 减少不必要的元素\n- 让空间呼吸\n## 自然光\n- 引入充足的自然光\n- 感受时间的变化\n## 材质\n- 天然材质的温度\n- 材质与时间共生\n## 生活动线\n- 符合真实的生活习惯\n- 让动线更自然流畅\n</script>',
    };
  if (endpoint === "quiz")
    return {
      title: report.video_name,
      question_count: questions.length,
      type_stats: { 单选: 1, 多选: 1, 判断: 1 },
      questions: questions.map(
        ({ answer: _answer, explanation: _explanation, ...question }) =>
          question,
      ),
      attempts: [],
    };
  if (endpoint === "quiz/submit") {
    const graded = questions.map((question) => {
      const given = body.answers[question.id] || [];
      const correct =
        given.length === question.answer.length &&
        given.every((value) => question.answer.includes(value));
      return {
        ...question,
        your_answer: given,
        verdict: correct ? "correct" : "wrong",
      };
    });
    const correct = graded.filter(
      (question) => question.verdict === "correct",
    ).length;
    return {
      attempt_id: "preview",
      score: Math.round((correct / questions.length) * 100),
      correct_count: correct,
      question_count: questions.length,
      questions: graded,
      per_type: {},
      per_chapter: [],
    };
  }
  if (endpoint === "quiz/advice")
    return {
      advice: "预览建议：回顾留白与自然光章节，结合自己的生活空间举一个例子。",
    };
  if (endpoint === "knowledge-graph")
    return {
      html:
        "const graphData = " +
        JSON.stringify({
          nodes: [
            { name: "空间设计", desc: "让空间回归人的真实需求。" },
            { name: "自然光", desc: "感受时间与情绪的变化。" },
            { name: "留白", desc: "减少视觉干扰。" },
            { name: "材质", desc: "真实的触感。" },
            { name: "生活动线", desc: "符合生活习惯。" },
          ],
          links: [
            { source: "空间设计", target: "自然光", relation: "引入" },
            { source: "空间设计", target: "留白", relation: "保留" },
            { source: "空间设计", target: "材质", relation: "运用" },
            { source: "空间设计", target: "生活动线", relation: "组织" },
          ],
        }) +
        "; const chart = null;",
    };
  return null;
}
