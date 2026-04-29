using BGGAPI.Src.Entities.Dtos;

namespace BGGAPI.Src.Services.Interfaces;

public interface IBoardGameService
{
    Task<BoardGameDto> GetByIdAsync(int id);
    Task<BoardGameDto> GetCardByIdAsync(int id);
    Task<IEnumerable<BoardGameDto>> GetCardsByIdAsync(IEnumerable<int> ids);
}