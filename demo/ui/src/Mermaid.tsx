import React, {useEffect, useState} from "react";
import mermaid from "mermaid";

interface MermaidChartProps {
  chart: string;
}

mermaid.initialize({
  startOnLoad: true,
  theme: "default",
});

export const MermaidChart: React.FC<MermaidChartProps> = ({ chart }) => {
  const [svgSource, setSvgSource] = useState<string>('');

  useEffect(() => {
    console.log(chart);
    console.log('run use effect');
      mermaid.render('mermaid-chart', chart).then((result) => {
        setSvgSource(result.svg);
      });
  }, [chart]);

  return <div dangerouslySetInnerHTML={{ __html: svgSource}}/>
}

