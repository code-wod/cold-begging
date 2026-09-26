const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: {
    'background/service-worker': './src/background/service-worker.ts',
    'content/content-script': './src/content/content-script.ts',
    'sidepanel/app': './src/sidepanel/main.tsx',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
    clean: true,
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        { from: 'manifest.json', to: 'manifest.json' },
        { from: 'icons', to: 'icons', noErrorOnMissing: true },
      ],
    }),
    new HtmlWebpackPlugin({
      template: './src/sidepanel/index.html',
      filename: 'src/sidepanel/index.html',
      chunks: ['sidepanel/app'],
    }),
  ],
  optimization: {
    splitChunks: false,
  },
};
