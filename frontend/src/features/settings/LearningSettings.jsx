import { motion } from "framer-motion";
import { GraduationCap } from "lucide-react";

export default function LearningSettings({ model, activeSection }) {
  const { settings, form, setField } = model;
  return (
    <>
      {/* 默认学习阶段 */}
      <motion.section
        hidden={activeSection !== "learning"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center space-x-2">
          <GraduationCap className="w-5 h-5 text-primary-600" />
          <span>默认学习阶段</span>
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          {(settings.education_levels || ["小学", "初中", "高中"]).map(
            (level) => (
              <button
                key={level}
                onClick={() => setField("default_education_level", level)}
                className={`px-6 py-2.5 rounded-lg border-2 font-medium text-sm transition ${form.default_education_level === level ? "border-primary-500 bg-primary-50 text-primary-700" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}
              >
                {level}
              </button>
            ),
          )}
        </div>
        <p className="mt-3 text-sm text-gray-500">
          上传视频时也可单独选择学习阶段，此处为未指定时的默认值。
        </p>
      </motion.section>
    </>
  );
}
