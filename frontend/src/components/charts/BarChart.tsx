'use client';
import ReactECharts from 'echarts-for-react';

interface BarChartProps {
  data: { name: string; value: number }[];
  title?: string;
  xAxisName?: string;
  yAxisName?: string;
}

export default function BarChart({ data, title, xAxisName, yAxisName }: BarChartProps) {
  const option = {
    title: {
      text: title,
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(d => d.name),
      name: xAxisName,
      axisLabel: {
        interval: 0,
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: yAxisName
    },
    series: [
      {
        data: data.map(d => d.value),
        type: 'bar',
        itemStyle: {
          color: '#3b82f6' // tailwind blue-500
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '400px', width: '100%' }} />;
}
