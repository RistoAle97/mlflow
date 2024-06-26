import { useMemo } from 'react';
import type { RunsChartsRunData } from '../RunsCharts.common';
import { RunsMetricsBarPlot } from '../RunsMetricsBarPlot';
import { useRunsChartsTooltip } from '../../hooks/useRunsChartsTooltip';
import type { RunsChartsBarCardConfig } from '../../runs-charts.types';
import { useIsInViewport } from '../../hooks/useIsInViewport';
import { shouldUseNewRunRowsVisibilityModel } from '../../../../../common/utils/FeatureUtils';
import {
  RunsChartCardWrapper,
  type RunsChartCardReorderProps,
  RunsChartsChartsDragGroup,
  ChartRunsCountIndicator,
  RunsChartCardFullScreenProps,
} from './ChartCard.common';
import { useChartImageDownloadHandler } from '../../hooks/useChartImageDownloadHandler';
import { downloadChartDataCsv } from '../../../experiment-page/utils/experimentPage.common-utils';

export interface RunsChartsBarChartCardProps extends RunsChartCardReorderProps, RunsChartCardFullScreenProps {
  config: RunsChartsBarCardConfig;
  chartRunData: RunsChartsRunData[];

  onDelete: () => void;
  onEdit: () => void;
}

export const barChartCardDefaultMargin = {
  t: 24,
  b: 48,
  r: 0,
  l: 4,
  pad: 0,
};

export const RunsChartsBarChartCard = ({
  config,
  chartRunData,
  onDelete,
  onEdit,
  onReorderWith,
  canMoveDown,
  canMoveUp,
  onMoveDown,
  onMoveUp,
  fullScreen,
  setFullScreenChart,
}: RunsChartsBarChartCardProps) => {
  const toggleFullScreenChart = () => {
    setFullScreenChart?.({
      config,
      title: config.metricKey,
      subtitle: <ChartRunsCountIndicator runsOrGroups={chartRunData} />,
    });
  };

  const slicedRuns = useMemo(() => {
    if (shouldUseNewRunRowsVisibilityModel()) {
      return chartRunData.filter(({ hidden }) => !hidden).reverse();
    }
    return chartRunData.slice(0, config.runsCountToCompare || 10).reverse();
  }, [chartRunData, config]);

  const { setTooltip, resetTooltip, selectedRunUuid } = useRunsChartsTooltip(config);

  const { elementRef, isInViewport } = useIsInViewport();

  const [imageDownloadHandler, setImageDownloadHandler] = useChartImageDownloadHandler();

  const chartBody = (
    <div
      css={[
        styles.barChartCardWrapper,
        {
          height: fullScreen ? '100%' : undefined,
        },
      ]}
      ref={elementRef}
    >
      {isInViewport ? (
        <RunsMetricsBarPlot
          runsData={slicedRuns}
          metricKey={config.metricKey}
          displayRunNames={false}
          displayMetricKey={false}
          useDefaultHoverBox={false}
          margin={barChartCardDefaultMargin}
          onHover={setTooltip}
          onUnhover={resetTooltip}
          selectedRunUuid={selectedRunUuid}
          onSetDownloadHandler={setImageDownloadHandler}
        />
      ) : null}
    </div>
  );

  if (fullScreen) {
    return chartBody;
  }

  return (
    <RunsChartCardWrapper
      onEdit={onEdit}
      onDelete={onDelete}
      title={config.metricKey}
      subtitle={<ChartRunsCountIndicator runsOrGroups={slicedRuns} />}
      uuid={config.uuid}
      dragGroupKey={RunsChartsChartsDragGroup.GENERAL_AREA}
      onReorderWith={onReorderWith}
      canMoveDown={canMoveDown}
      canMoveUp={canMoveUp}
      onMoveDown={onMoveDown}
      onMoveUp={onMoveUp}
      toggleFullScreenChart={toggleFullScreenChart}
      supportedDownloadFormats={['png', 'svg', 'csv']}
      onClickDownload={(format) => {
        if (format === 'csv' || format === 'csv-full') {
          const runsToExport = [...slicedRuns].reverse();
          downloadChartDataCsv(runsToExport, [config.metricKey], [], config.metricKey);
          return;
        }
        imageDownloadHandler?.(format, config.metricKey);
      }}
    >
      {chartBody}
    </RunsChartCardWrapper>
  );
};

const styles = {
  barChartCardWrapper: {
    overflow: 'hidden',
  },
};
