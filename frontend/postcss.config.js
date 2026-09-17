export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
    'postcss-pxtorem': { rootValue: 16, propList: ['*'], mediaQuery: true, minPixelValue: 0 },
  },
};
