'use client';
import ReactECharts from 'echarts-for-react';

interface BoxPlotProps {
  categories: string[];
  data: number[][]; // [min, Q1, median, Q3, max] for each category
  title?: string;
}

export default function BoxPlot({ categories, data, title }: BoxPlotProps) {
  const option = {
    title: {
      text: title,
      left: 'center',
    },
    tooltip: {
      trigger: 'item',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: categories,
      boundaryGap: true,
      nameGap: 30,
      splitArea: {
        show: false
      },
      axisLabel: {
        formatter: '{value}'
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: 'Relative Abundance',
      splitArea: {
        show: true
      }
    },
    series: [
      {
        name: 'boxplot',
        type: 'boxplot',
        data: data,
        itemStyle: {
          color: '#cbd5e1', // slate-300
          borderColor: '#475569' // slate-600
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '400px', width: '100%' }} />;
}
