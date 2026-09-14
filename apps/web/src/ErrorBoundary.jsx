import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(previous) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey) this.setState({ failed: false });
  }
  render() {
    if (this.state.failed) return <div className="error" role="alert">这部分内容暂时无法显示。可以继续阅读或重新提问。</div>;
    return this.props.children;
  }
}
