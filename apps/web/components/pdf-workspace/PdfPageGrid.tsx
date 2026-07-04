'use client';

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { PdfPageCard } from './PdfPageCard';

const GRID_CLASSES = 'grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5';

function SortablePageCard({
  pageNumber,
  displayPosition,
  renderThumbnail,
}: {
  pageNumber: number;
  displayPosition: number;
  renderThumbnail: (pageNumber: number, targetWidth: number) => Promise<string>;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: pageNumber,
  });

  return (
    <PdfPageCard
      pageNumber={pageNumber}
      displayPosition={displayPosition}
      renderThumbnail={renderThumbnail}
      setNodeRef={setNodeRef}
      dragHandleProps={{ attributes, listeners }}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
    />
  );
}

export function PdfPageGrid({
  mode,
  pageOrder,
  selectedPages,
  renderThumbnail,
  onToggleSelect,
  onReorder,
}: {
  mode: 'select' | 'reorder';
  /** Page numbers in current visual order — identity `[1..pageCount]` for
   * select mode, or the live user-reordered sequence in reorder mode. */
  pageOrder: number[];
  selectedPages?: ReadonlySet<number>;
  renderThumbnail: (pageNumber: number, targetWidth: number) => Promise<string>;
  onToggleSelect?: (pageNumber: number) => void;
  onReorder?: (fromIndex: number, toIndex: number) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  if (mode === 'reorder') {
    const handleDragEnd = (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const fromIndex = pageOrder.indexOf(Number(active.id));
      const toIndex = pageOrder.indexOf(Number(over.id));
      if (fromIndex === -1 || toIndex === -1) return;
      onReorder?.(fromIndex, toIndex);
    };

    return (
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={pageOrder} strategy={rectSortingStrategy}>
          <div className={GRID_CLASSES}>
            {pageOrder.map((pageNumber, index) => (
              <SortablePageCard
                key={pageNumber}
                pageNumber={pageNumber}
                displayPosition={index + 1}
                renderThumbnail={renderThumbnail}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    );
  }

  return (
    <div className={GRID_CLASSES}>
      {pageOrder.map((pageNumber, index) => (
        <PdfPageCard
          key={pageNumber}
          pageNumber={pageNumber}
          displayPosition={index + 1}
          renderThumbnail={renderThumbnail}
          selected={selectedPages?.has(pageNumber)}
          onSelectToggle={() => onToggleSelect?.(pageNumber)}
        />
      ))}
    </div>
  );
}
