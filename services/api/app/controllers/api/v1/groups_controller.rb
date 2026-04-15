module Api
  module V1
    class GroupsController < BaseController
      def create
        group = Group.create!(group_params)
        render json: serialize(group), status: :created
      end

      def show
        group = Group.find_by!(code: params[:id])
        render json: serialize(group).merge(sessions: group.visit_sessions.pluck(:id))
      end

      private

      def group_params
        params.require(:group).permit(:name)
      end

      def serialize(group)
        { id: group.id, code: group.code, name: group.name }
      end
    end
  end
end
