using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Core.Models;
using Mes.Wpf.Modules.Drawings.Dtos;
using System;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Infrastructure.Api
{
    public class DrawingViewer : IDrawingViewer
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly IDrawingFileOpener _drawingFileOpener;

        public DrawingViewer(
            IApiClient apiClient,
            IMessageService messageService,
            IDrawingFileOpener drawingFileOpener)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _drawingFileOpener = drawingFileOpener;
        }

        public async Task OpenCurrentDrawingAsync(long drawingId)
        {
            if (drawingId <= 0)
            {
                _messageService.ShowWarning("도면 정보가 없습니다.");
                return;
            }

            var drawingResult = await _apiClient.GetAsync<DrawingDto>($"{ApiRoutes.Drawings}/{drawingId}");
            if (!drawingResult.Success || drawingResult.Data == null)
            {
                _messageService.ShowError(drawingResult.Message ?? "도면 정보를 조회할 수 없습니다.");
                return;
            }

            if (!drawingResult.Data.CurrentRevisionId.HasValue || drawingResult.Data.CurrentRevisionId.Value <= 0)
            {
                _messageService.ShowWarning("현재 리비전이 없는 도면입니다.");
                return;
            }

            var filesResult = await _apiClient.GetAsync<PagedResult<DrawingRevisionFileDto>>(
                $"{ApiRoutes.Drawings}/{drawingId}/revisions/{drawingResult.Data.CurrentRevisionId.Value}/files");

            if (!filesResult.Success || filesResult.Data == null)
            {
                _messageService.ShowError(filesResult.Message ?? "도면 파일 정보를 조회할 수 없습니다.");
                return;
            }

            var drawingFile = filesResult.Data.Items
                .FirstOrDefault(x => string.Equals(x.FileKind, "DRAWING", StringComparison.OrdinalIgnoreCase));

            if (drawingFile == null || drawingFile.RevisionFileId <= 0)
            {
                _messageService.ShowWarning("열 수 있는 도면 파일이 없습니다.");
                return;
            }

            var url = _apiClient.BuildAbsoluteUrl(
                $"{ApiRoutes.Drawings}/revision-files/{drawingFile.RevisionFileId}/download");

            await _drawingFileOpener.OpenRevisionFileAsync(url, drawingFile.OriginalFilename);
        }
    }
}